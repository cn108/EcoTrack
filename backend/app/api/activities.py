import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, get_db
from app.models.activity import Activity
from app.models.category import Category
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityResponse, ActivityUpdate
from app.services.carbon_calculator import calculate_co2e
from app.services.emission_factor_resolver import (
    AmbiguousEmissionFactorError,
    EmissionFactorNotFoundError,
    InactiveEmissionFactorError,
    UnsupportedActivityUnitError,
    resolve_emission_factor,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/activities", tags=["activities"])
PRICE_TRACKED_FUEL_TYPES = {
    "car_petrol",
    "car_diesel",
    "generator_petrol",
    "generator_diesel",
    "cooking_lpg",
    "cooking_kerosene",
}


def _get_category(session: Session, category_id: UUID) -> Category:
    category = session.get(Category, category_id)
    if category is None or not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Category is invalid or inactive",
        )
    return category


def _get_emission_factor(session: Session, category: Category, activity_type: str, unit: str):
    try:
        return resolve_emission_factor(session, category, activity_type, unit)
    except EmissionFactorNotFoundError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UnsupportedActivityUnitError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except (InactiveEmissionFactorError, AmbiguousEmissionFactorError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        logger.error(
            "activity_write_conflict",
            extra={"error_type": type(error).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Activity could not be saved because of a data conflict",
        ) from error
    except SQLAlchemyError as error:
        session.rollback()
        logger.error(
            "activity_database_error",
            extra={"error_type": type(error).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Activity could not be saved",
        ) from error


@router.post(
    "",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an activity",
    description=(
        "Resolves an active emission factor for the category, activity type, and unit, "
        "calculates CO2e on the server, and stores the selected factor reference."
    ),
    responses={
        401: {"description": "Access token is invalid, expired, or the account is inactive"},
        409: {"description": "The factor is inactive, ambiguous, or conflicts with stored data"},
        500: {"description": "The activity could not be saved"},
    },
)
def create_activity(
    payload: ActivityCreate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Activity:
    if payload.unit_cost_ngn is not None and payload.activity_type not in PRICE_TRACKED_FUEL_TYPES:
        raise HTTPException(
            status_code=422,
            detail="Per-unit naira prices are currently supported for fuel activities",
        )
    category = _get_category(session, payload.category_id)
    factor = _get_emission_factor(
        session, category, payload.activity_type, payload.unit
    )
    try:
        calculated_co2e = calculate_co2e(payload.quantity, factor.factor_value)
    except (TypeError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    activity = Activity(
        user_id=current_user.id,
        category=category,
        activity_type=payload.activity_type,
        quantity=payload.quantity,
        unit=payload.unit,
        activity_date=payload.activity_date,
        emission_factor=factor,
        calculated_co2e=calculated_co2e,
        unit_cost_ngn=payload.unit_cost_ngn,
        notes=payload.notes,
    )
    session.add(activity)
    _commit(session)
    logger.info(
        "activity_created",
        extra={
            "activity_id": str(activity.id),
            "emission_factor_id": str(factor.id),
        },
    )
    return activity


@router.get(
    "",
    response_model=list[ActivityResponse],
    summary="List the current user's activities",
    description=(
        "Returns only activities owned by the Bearer-token authenticated user. "
        "Use skip and limit for pagination; filters may be combined."
    ),
    responses={
        401: {"description": "Access token is invalid, expired, or the account is inactive"},
    },
)
def list_activities(
    category_id: UUID | None = None,
    activity_type: str | None = Query(default=None, min_length=1, max_length=100),
    start_date: date | None = None,
    end_date: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Activity]:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")

    statement = (
        select(Activity)
        .options(joinedload(Activity.category), joinedload(Activity.emission_factor))
        .where(Activity.user_id == current_user.id)
    )
    if category_id is not None:
        statement = statement.where(Activity.category_id == category_id)
    if activity_type is not None:
        statement = statement.where(Activity.activity_type == activity_type.strip())
    if start_date is not None:
        statement = statement.where(Activity.activity_date >= start_date)
    if end_date is not None:
        statement = statement.where(Activity.activity_date <= end_date)
    statement = statement.order_by(
        Activity.activity_date.desc(), Activity.created_at.desc()
    ).offset(skip).limit(limit)
    return list(session.scalars(statement).all())


def _get_owned_activity(session: Session, activity_id: UUID, user_id: UUID) -> Activity:
    activity = session.scalar(
        select(Activity)
        .options(joinedload(Activity.category), joinedload(Activity.emission_factor))
        .where(Activity.id == activity_id, Activity.user_id == user_id)
    )
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")
    return activity


@router.get(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Get one of the current user's activities",
    responses={
        401: {"description": "Access token is invalid, expired, or the account is inactive"},
        404: {"description": "Activity not found"},
    },
)
def get_activity(
    activity_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Activity:
    return _get_owned_activity(session, activity_id, current_user.id)


@router.put(
    "/{activity_id}",
    response_model=ActivityResponse,
    summary="Update one of the current user's activities",
    description=(
        "Updates supplied editable fields. Quantity changes are recalculated with the "
        "activity's existing factor; changes to category, activity type, or unit resolve "
        "a new unique active factor."
    ),
    responses={
        401: {"description": "Access token is invalid, expired, or the account is inactive"},
        404: {"description": "Activity not found"},
        409: {"description": "The matching factor is inactive or ambiguous"},
        500: {"description": "The activity could not be saved"},
    },
)
def update_activity(
    activity_id: UUID,
    payload: ActivityUpdate,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Activity:
    activity = _get_owned_activity(session, activity_id, current_user.id)
    fields = payload.model_fields_set
    category = (
        _get_category(session, payload.category_id)
        if "category_id" in fields
        else activity.category
    )
    activity_type = payload.activity_type if "activity_type" in fields else activity.activity_type
    unit = payload.unit if "unit" in fields else activity.unit
    quantity = payload.quantity if "quantity" in fields else activity.quantity
    unit_cost_ngn = (
        payload.unit_cost_ngn
        if "unit_cost_ngn" in fields
        else activity.unit_cost_ngn
    )

    if (
        "unit_cost_ngn" in fields
        and unit_cost_ngn is not None
        and activity_type not in PRICE_TRACKED_FUEL_TYPES
    ):
        raise HTTPException(
            status_code=422,
            detail="Per-unit naira prices are currently supported for fuel activities",
        )

    factor_context_changed = (
        category.id != activity.category_id
        or activity_type != activity.activity_type
        or unit != activity.unit
    )
    quantity_changed = quantity != activity.quantity
    factor = (
        _get_emission_factor(session, category, activity_type, unit)
        if factor_context_changed
        else activity.emission_factor
    )
    calculated_co2e = activity.calculated_co2e
    if factor_context_changed or quantity_changed:
        try:
            calculated_co2e = calculate_co2e(quantity, factor.factor_value)
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    if "category_id" in fields:
        activity.category = category
    if "activity_type" in fields:
        activity.activity_type = activity_type
    if "unit" in fields:
        activity.unit = unit
    if "quantity" in fields:
        activity.quantity = quantity
    if "activity_date" in fields:
        activity.activity_date = payload.activity_date
    if activity_type not in PRICE_TRACKED_FUEL_TYPES:
        activity.unit_cost_ngn = None
    elif "unit_cost_ngn" in fields:
        activity.unit_cost_ngn = unit_cost_ngn
    if "notes" in fields:
        activity.notes = payload.notes
    if factor_context_changed:
        activity.emission_factor = factor
    if factor_context_changed or quantity_changed:
        activity.calculated_co2e = calculated_co2e

    _commit(session)
    logger.info(
        "activity_updated",
        extra={"activity_id": str(activity.id)},
    )
    return activity


@router.delete(
    "/{activity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one of the current user's activities",
    responses={
        401: {"description": "Access token is invalid, expired, or the account is inactive"},
        404: {"description": "Activity not found"},
        500: {"description": "The activity could not be deleted"},
    },
)
def delete_activity(
    activity_id: UUID,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    activity = _get_owned_activity(session, activity_id, current_user.id)
    session.delete(activity)
    _commit(session)
    logger.info("activity_deleted", extra={"activity_id": str(activity_id)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)