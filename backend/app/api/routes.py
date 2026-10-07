from __future__ import annotations

import json
import logging
import threading
import time
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.route_distance import RouteDistanceRequest, RouteDistanceResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/routes", tags=["routes"])
REQUEST_TIMEOUT_SECONDS = 12
NOMINATIM_MIN_INTERVAL_SECONDS = 1.0
GEOCODE_CACHE_SIZE = 512
OSM_USER_AGENT = "EcoTrack/0.2 (manual driving route calculator)"

_geocode_lock = threading.Lock()
_last_nominatim_request = 0.0
_geocode_cache: OrderedDict[str, tuple[float, float]] = OrderedDict()


def _fetch_json(url: str) -> object:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": OSM_USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read())
    except HTTPError as error:
        logger.warning(
            "openstreetmap_service_rejected",
            extra={"http_status": error.code, "host": request.host},
        )
        if error.code == 429:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The free OpenStreetMap service is busy. Wait a moment and try again, or enter the distance manually.",
            ) from error
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The free OpenStreetMap route service could not process this request. Try again or enter the distance manually.",
        ) from error
    except (TimeoutError, URLError, OSError) as error:
        logger.warning(
            "openstreetmap_service_unavailable",
            extra={"error_type": type(error).__name__, "host": request.host},
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="OpenStreetMap took too long to find this route. Try again or enter the distance manually.",
        ) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        logger.error(
            "openstreetmap_invalid_response",
            extra={"host": request.host, "error_type": type(error).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The OpenStreetMap service returned an unreadable response.",
        ) from error


def _geocode_location(location: str) -> tuple[float, float]:
    normalized_location = " ".join(location.split()).casefold()
    global _last_nominatim_request

    with _geocode_lock:
        cached = _geocode_cache.get(normalized_location)
        if cached is not None:
            _geocode_cache.move_to_end(normalized_location)
            return cached

        elapsed = time.monotonic() - _last_nominatim_request
        if elapsed < NOMINATIM_MIN_INTERVAL_SECONDS:
            time.sleep(NOMINATIM_MIN_INTERVAL_SECONDS - elapsed)

        query = urlencode({
            "q": location,
            "format": "jsonv2",
            "limit": 1,
        })
        _last_nominatim_request = time.monotonic()
        result = _fetch_json(f"{settings.osm_nominatim_url}?{query}")

        if not isinstance(result, list) or not result:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"OpenStreetMap could not find “{location}”. Try a more specific address, or enter the distance manually.",
            )
        place = result[0]
        try:
            latitude = float(place["lat"])
            longitude = float(place["lon"])
        except (KeyError, TypeError, ValueError) as error:
            logger.error("openstreetmap_geocode_response_invalid")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenStreetMap returned an invalid location result.",
            ) from error
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            logger.error("openstreetmap_geocode_coordinates_out_of_range")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="OpenStreetMap returned out-of-range location coordinates.",
            )

        coordinates = (latitude, longitude)
        _geocode_cache[normalized_location] = coordinates
        _geocode_cache.move_to_end(normalized_location)
        if len(_geocode_cache) > GEOCODE_CACHE_SIZE:
            _geocode_cache.popitem(last=False)
        return coordinates


def _read_openstreetmap_route(origin: str, destination: str) -> tuple[int, float]:
    origin_latitude, origin_longitude = _geocode_location(origin)
    destination_latitude, destination_longitude = _geocode_location(destination)
    coordinates = (
        f"{origin_longitude},{origin_latitude};"
        f"{destination_longitude},{destination_latitude}"
    )
    result = _fetch_json(
        f"{settings.osm_routing_url}/{coordinates}"
        "?overview=false&alternatives=false&steps=false"
    )
    if not isinstance(result, dict) or result.get("code") != "Ok":
        if isinstance(result, dict) and result.get("code") == "NoRoute":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="OpenStreetMap found no driving route between those locations. Check the addresses or enter the distance manually.",
            )
        logger.error(
            "openstreetmap_route_response_invalid",
            extra={"response_code": result.get("code") if isinstance(result, dict) else None},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenStreetMap returned an invalid route response.",
        )

    routes = result.get("routes")
    if not isinstance(routes, list) or not routes or not isinstance(routes[0], dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="OpenStreetMap found no driving route between those locations. Check the addresses or enter the distance manually.",
        )
    try:
        distance_meters = float(routes[0]["distance"])
        duration_seconds = float(routes[0]["duration"])
    except (KeyError, TypeError, ValueError) as error:
        logger.error("openstreetmap_route_response_missing_fields")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenStreetMap returned an incomplete route response.",
        ) from error
    if (
        not distance_meters >= 0
        or not duration_seconds >= 0
        or not distance_meters < float("inf")
        or not duration_seconds < float("inf")
    ):
        logger.error("openstreetmap_route_response_out_of_range")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OpenStreetMap returned invalid distance or duration values.",
        )

    return round(distance_meters), duration_seconds


@router.post(
    "/distance",
    response_model=RouteDistanceResponse,
    summary="Calculate a driving route distance with OpenStreetMap",
    responses={
        401: {"description": "Authentication is required"},
        422: {"description": "A location or driving route could not be found"},
        503: {"description": "The public OpenStreetMap service is busy"},
        504: {"description": "The OpenStreetMap route calculation timed out"},
    },
)
def calculate_route_distance(
    payload: RouteDistanceRequest,
    current_user: User = Depends(get_current_user),
) -> RouteDistanceResponse:
    del current_user
    distance_meters, duration_seconds = _read_openstreetmap_route(
        payload.origin,
        payload.destination,
    )
    return RouteDistanceResponse(
        distance_meters=distance_meters,
        distance_km=distance_meters / 1000,
        duration_seconds=duration_seconds,
    )
