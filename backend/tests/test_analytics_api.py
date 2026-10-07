import os
import unittest
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

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
from app.services.analytics import month_start, previous_month_start


class AnalyticsAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_ids: list[uuid.UUID] = []
        self.user_id = self._create_user()
        self.headers = {
            "Authorization": f"Bearer {create_access_token(self.user_id)}"
        }
        self.today = datetime.now(UTC).date()

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id.in_(self.user_ids)))
            session.commit()
        self.client.close()

    def _create_user(self) -> uuid.UUID:
        user_id = uuid.uuid4()
        with SessionLocal() as session:
            session.add(
                User(
                    id=user_id,
                    email=f"{user_id}@example.com",
                    password_hash="test-only-hash",
                    first_name="Analytics",
                    last_name="User",
                )
            )
            session.commit()
        self.user_ids.append(user_id)
        return user_id

    def _insert_activity(
        self,
        *,
        user_id: uuid.UUID,
        category_name: str,
        activity_type: str,
        activity_date: date,
        amount: str,
    ) -> None:
        with SessionLocal() as session:
            category = session.scalar(
                select(Category).where(Category.name == category_name)
            )
            factor = session.scalar(
                select(EmissionFactor).where(
                    EmissionFactor.category == category_name,
                    EmissionFactor.activity_type == activity_type,
                    EmissionFactor.is_active.is_(True),
                )
            )
            quantity = Decimal(amount)
            session.add(
                Activity(
                    user_id=user_id,
                    category_id=category.id,
                    activity_type=activity_type,
                    quantity=quantity,
                    unit=factor.factor_unit.removeprefix("kg_co2e_per_"),
                    activity_date=activity_date,
                    emission_factor_id=factor.id,
                    calculated_co2e=quantity * factor.factor_value,
                )
            )
            session.commit()

    def _seed_dashboard_activities(self) -> tuple[date, date, uuid.UUID]:
        current_start = month_start(self.today)
        previous_start = previous_month_start(self.today)
        previous_day = previous_start + timedelta(days=1)
        other_user_id = self._create_user()

        self._insert_activity(
            user_id=self.user_id,
            category_name="Transport",
            activity_type="car_petrol",
            activity_date=self.today,
            amount="2",
        )
        self._insert_activity(
            user_id=self.user_id,
            category_name="Energy",
            activity_type="electricity",
            activity_date=current_start,
            amount="10",
        )
        self._insert_activity(
            user_id=self.user_id,
            category_name="Transport",
            activity_type="car_petrol",
            activity_date=previous_day,
            amount="4",
        )
        self._insert_activity(
            user_id=other_user_id,
            category_name="Food",
            activity_type="beef",
            activity_date=self.today,
            amount="100",
        )
        return previous_start, current_start, other_user_id

    def test_dashboard_totals_categories_recent_and_user_isolation(self) -> None:
        self._seed_dashboard_activities()
        response = self.client.get("/dashboard", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        expected_current = Decimal("4.572000") + Decimal("5.441321")
        expected_previous = Decimal("9.144000")
        self.assertEqual(Decimal(data["current_month_total_co2e"]), expected_current)
        self.assertEqual(
            Decimal(data["previous_month_total_co2e"]), expected_previous
        )
        self.assertEqual(
            Decimal(data["percentage_change_percent"]),
            ((expected_current - expected_previous) / expected_previous * 100).quantize(Decimal("0.01")),
        )
        self.assertEqual(
            Decimal(data["daily_average_co2e"]),
            (expected_current / Decimal(self.today.day)).quantize(Decimal("0.000001")),
        )
        self.assertEqual(data["activities_this_month"], 2)
        self.assertEqual(data["highest_emission_category"]["category_name"], "Energy")
        self.assertEqual(
            data["highest_emission_activity_type"]["activity_type"], "electricity"
        )
        self.assertEqual(
            {row["category_name"] for row in data["category_totals"]},
            {"Transport", "Energy"},
        )
        self.assertEqual(len(data["recent_activities"]), 3)
        self.assertNotIn("Food", {row["category"]["name"] for row in data["recent_activities"]})

    def test_monthly_category_and_activity_type_aggregations(self) -> None:
        previous_start, current_start, _ = self._seed_dashboard_activities()
        monthly = self.client.get(
            "/analytics/monthly",
            headers=self.headers,
            params={"start_date": previous_start.isoformat(), "end_date": self.today.isoformat()},
        )
        self.assertEqual(monthly.status_code, 200, monthly.text)
        monthly_totals = {row["month"]: Decimal(row["total_co2e"]) for row in monthly.json()}
        self.assertEqual(monthly_totals[previous_start.strftime("%Y-%m")], Decimal("9.144000"))
        self.assertEqual(monthly_totals[current_start.strftime("%Y-%m")], Decimal("10.013321"))

        categories = self.client.get("/analytics/categories", headers=self.headers)
        self.assertEqual(categories.status_code, 200, categories.text)
        category_totals = {
            row["category_name"]: Decimal(row["total_co2e"])
            for row in categories.json()
        }
        self.assertEqual(category_totals, {"Transport": Decimal("13.716000"), "Energy": Decimal("5.441321")})

        activity_types = self.client.get("/analytics/activity-types", headers=self.headers)
        self.assertEqual(activity_types.status_code, 200, activity_types.text)
        type_totals = {
            row["activity_type"]: Decimal(row["total_co2e"])
            for row in activity_types.json()
        }
        self.assertEqual(
            type_totals,
            {"car_petrol": Decimal("13.716000"), "electricity": Decimal("5.441321")},
        )

    def test_empty_dashboard_and_analytics(self) -> None:
        response = self.client.get("/dashboard", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(Decimal(data["current_month_total_co2e"]), Decimal("0"))
        self.assertIsNone(data["percentage_change_percent"])
        self.assertIsNone(data["highest_emission_category"])
        self.assertEqual(data["category_totals"], [])
        self.assertEqual(data["recent_activities"], [])

        categories = self.client.get("/analytics/categories", headers=self.headers)
        activity_types = self.client.get("/analytics/activity-types", headers=self.headers)
        self.assertEqual(categories.json(), [])
        self.assertEqual(activity_types.json(), [])

    def test_dashboard_and_analytics_reject_unauthenticated_requests(self) -> None:
        for path in (
            "/dashboard",
            "/analytics/monthly",
            "/analytics/categories",
            "/analytics/activity-types",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)


if __name__ == "__main__":
    unittest.main()