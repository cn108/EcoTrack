import os
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.api.routes import _read_openstreetmap_route
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


class RouteDistanceAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_id = uuid.uuid4()
        with SessionLocal() as session:
            session.add(
                User(
                    id=self.user_id,
                    email=f"{self.user_id}@test.invalid",
                    password_hash="test-only-hash",
                    first_name="Test",
                    last_name="User",
                )
            )
            session.commit()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(str(self.user_id))}",
        }
        self.payload = {
            "origin": "Home, Ikeja, Lagos",
            "destination": "Office, Victoria Island, Lagos",
        }

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id == self.user_id))
            session.commit()

    def test_calculates_driving_distance_and_duration(self) -> None:
        with patch("app.api.routes._read_openstreetmap_route", return_value=(12500, 900)):
            response = self.client.post(
                "/routes/distance",
                headers=self.headers,
                json=self.payload,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {
            "distance_meters": 12500,
            "distance_km": 12.5,
            "duration_seconds": 900.0,
        })

    def test_route_calculation_requires_authentication(self) -> None:
        response = self.client.post("/routes/distance", json=self.payload)
        self.assertEqual(response.status_code, 401)

    def test_identical_locations_are_rejected(self) -> None:
        response = self.client.post(
            "/routes/distance",
            headers=self.headers,
            json={"origin": "Lagos", "destination": "lagos"},
        )
        self.assertEqual(response.status_code, 422)

    def test_reads_osrm_route_with_coordinates_in_longitude_latitude_order(self) -> None:
        with (
            patch(
                "app.api.routes._geocode_location",
                side_effect=[(6.6, 3.3), (6.4, 3.4)],
            ),
            patch(
                "app.api.routes._fetch_json",
                return_value={
                    "code": "Ok",
                    "routes": [{"distance": 12549.7, "duration": 900.25}],
                },
            ) as mock_fetch,
        ):
            result = _read_openstreetmap_route("Home, Lagos", "Office, Lagos")

        self.assertEqual(result, (12550, 900.25))
        self.assertIn("/3.3,6.6;3.4,6.4?", mock_fetch.call_args.args[0])
        self.assertIn("overview=false", mock_fetch.call_args.args[0])

    def test_no_driving_route_returns_actionable_validation_error(self) -> None:
        with (
            patch("app.api.routes._geocode_location", side_effect=[(6.6, 3.3), (6.4, 3.4)]),
            patch("app.api.routes._fetch_json", return_value={"code": "NoRoute", "routes": []}),
        ):
            with self.assertRaises(HTTPException) as raised:
                _read_openstreetmap_route("Island", "Remote location")

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn("enter the distance manually", raised.exception.detail)

    def test_invalid_route_distance_is_rejected(self) -> None:
        with (
            patch("app.api.routes._geocode_location", side_effect=[(6.6, 3.3), (6.4, 3.4)]),
            patch(
                "app.api.routes._fetch_json",
                return_value={"code": "Ok", "routes": [{"distance": float("nan"), "duration": 900}]},
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                _read_openstreetmap_route("Home", "Office")

        self.assertEqual(raised.exception.status_code, 502)
