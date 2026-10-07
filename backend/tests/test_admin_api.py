import os
import unittest
import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.activity import Activity
from app.models.category import Category
from app.models.emission_factor import EmissionFactor
from app.models.user import User


class AdminAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.admin_email = f"{uuid.uuid4()}@example.com"
        self.admin = self._new_user(self.admin_email, "Administrator", verified=True)
        self.member = self._new_user(f"{uuid.uuid4()}@example.com", "Member")
        self.inactive_member = self._new_user(
            f"{uuid.uuid4()}@example.com",
            "Inactive",
            active=False,
        )
        self.admin_headers = self._headers(self.admin.id)
        self.member_headers = self._headers(self.member.id)

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(
                User.id.in_((self.admin.id, self.member.id, self.inactive_member.id))
            ))
            session.commit()
        self.client.close()

    def _new_user(
        self,
        email: str,
        first_name: str,
        *,
        active: bool = True,
        verified: bool = False,
    ) -> User:
        user = User(
            email=email,
            password_hash="test-only-hash",
            first_name=first_name,
            last_name="User",
            is_active=active,
            is_verified=verified,
        )
        with SessionLocal() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)
        return user

    @staticmethod
    def _headers(user_id: uuid.UUID) -> dict[str, str]:
        return {"Authorization": f"Bearer {create_access_token(user_id)}"}

    def _create_member_activities(self) -> None:
        with SessionLocal() as session:
            transport = session.scalar(
                select(Category).where(Category.name == "Transport")
            )
            energy = session.scalar(select(Category).where(Category.name == "Energy"))
            petrol = session.scalar(
                select(EmissionFactor).where(
                    EmissionFactor.activity_type == "car_petrol",
                    EmissionFactor.is_active.is_(True),
                )
            )
            generator = session.scalar(
                select(EmissionFactor).where(
                    EmissionFactor.activity_type == "generator_petrol",
                    EmissionFactor.is_active.is_(True),
                )
            )
            if transport is None or energy is None or petrol is None or generator is None:
                self.fail("Required activity fixtures are missing from the migrated test database")

            session.add_all([
                Activity(
                    user_id=self.member.id,
                    category_id=transport.id,
                    activity_type="car_petrol",
                    quantity=Decimal("10"),
                    unit="L",
                    activity_date=date(2026, 1, 15),
                    emission_factor_id=petrol.id,
                    calculated_co2e=Decimal("22.860000"),
                    unit_cost_ngn=Decimal("500"),
                    notes="Private route note",
                ),
                Activity(
                    user_id=self.member.id,
                    category_id=energy.id,
                    activity_type="generator_petrol",
                    quantity=Decimal("5"),
                    unit="L",
                    activity_date=date(2026, 2, 15),
                    emission_factor_id=generator.id,
                    calculated_co2e=Decimal("11.430000"),
                    unit_cost_ngn=Decimal("600"),
                    notes="Private household note",
                ),
            ])
            session.commit()

    def test_admin_api_requires_authentication_and_configured_verified_admin(self) -> None:
        self.assertEqual(self.client.get("/admin/users").status_code, 401)
        with patch("app.api.admin.settings.admin_email", None):
            not_configured = self.client.get("/admin/users", headers=self.admin_headers)
        self.assertEqual(not_configured.status_code, 403)

        with patch("app.api.admin.settings.admin_email", self.admin_email):
            forbidden = self.client.get("/admin/users", headers=self.member_headers)
        self.assertEqual(forbidden.status_code, 403)

        unverified_email = f"{uuid.uuid4()}@example.com"
        unverified = self._new_user(unverified_email, "Unverified")
        try:
            with patch("app.api.admin.settings.admin_email", unverified_email):
                response = self.client.get(
                    "/admin/users",
                    headers=self._headers(unverified.id),
                )
            self.assertEqual(response.status_code, 403)
        finally:
            with SessionLocal() as session:
                session.execute(delete(User).where(User.id == unverified.id))
                session.commit()

    def test_user_search_status_filter_and_pagination(self) -> None:
        with patch("app.api.admin.settings.admin_email", self.admin_email):
            response = self.client.get(
                "/admin/users",
                params={"search": "example.com", "is_active": "true", "limit": 1},
                headers=self.admin_headers,
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["items"]), 1)
        self.assertEqual(body["limit"], 1)

        with patch("app.api.admin.settings.admin_email", self.admin_email):
            inactive = self.client.get(
                "/admin/users",
                params={"is_active": "false"},
                headers=self.admin_headers,
            )
        self.assertEqual(inactive.status_code, 200)
        self.assertEqual(inactive.json()["total"], 1)
        self.assertEqual(inactive.json()["items"][0]["id"], str(self.inactive_member.id))

    def test_user_activities_are_filterable_and_omit_private_fields(self) -> None:
        self._create_member_activities()
        with patch("app.api.admin.settings.admin_email", self.admin_email):
            response = self.client.get(
                f"/admin/users/{self.member.id}/activities",
                params={
                    "category": "Energy",
                    "date_from": "2026-02-01",
                    "date_to": "2026-02-28",
                },
                headers=self.admin_headers,
            )
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["items"]), 1)
        activity = body["items"][0]
        self.assertEqual(activity["activity_type"], "generator_petrol")
        self.assertEqual(activity["category"], "Energy")
        self.assertIn("source_name", activity)
        self.assertNotIn("notes", activity)
        self.assertNotIn("unit_cost_ngn", activity)
        self.assertNotIn("email", activity)

    def test_invalid_date_range_and_missing_target_are_rejected(self) -> None:
        with patch("app.api.admin.settings.admin_email", self.admin_email):
            invalid_range = self.client.get(
                "/admin/users",
                params={
                    "created_from": (date.today() + timedelta(days=1)).isoformat(),
                    "created_to": date.today().isoformat(),
                },
                headers=self.admin_headers,
            )
            missing_user = self.client.get(
                f"/admin/users/{uuid.uuid4()}/activities",
                headers=self.admin_headers,
            )
        self.assertEqual(invalid_range.status_code, 422)
        self.assertEqual(missing_user.status_code, 404)


if __name__ == "__main__":
    unittest.main()
