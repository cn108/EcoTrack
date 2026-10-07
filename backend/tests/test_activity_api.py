import os
import unittest
import uuid
from decimal import Decimal

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.core.security import create_access_token
from app.main import app
from app.models.activity import Activity
from app.models.category import Category
from app.models.emission_factor import EmissionFactor
from app.models.user import User


class ActivityAPITests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_ids: list[uuid.UUID] = []
        self.user_id = self._create_user()
        self.headers = {"Authorization": f"Bearer {create_access_token(self.user_id)}"}
        self.transport_id = self._category_id("Transport")
        self.energy_id = self._category_id("Energy")
        self.food_id = self._category_id("Food")

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id.in_(self.user_ids)))
            session.commit()

    def _create_user(self) -> uuid.UUID:
        user_id = uuid.uuid4()
        with SessionLocal() as session:
            session.add(
                User(
                    id=user_id,
                    email=f"{user_id}@test.invalid",
                    password_hash="test-only-hash",
                    first_name="Test",
                    last_name="User",
                )
            )
            session.commit()
        self.user_ids.append(user_id)
        return user_id

    @staticmethod
    def _category_id(name: str) -> uuid.UUID:
        with SessionLocal() as session:
            return session.scalar(select(Category.id).where(Category.name == name))

    def _payload(
        self,
        *,
        category_id: uuid.UUID | None = None,
        activity_type: str = "car_petrol",
        quantity: int | float | str = 2,
        unit: str = "L",
        activity_date: str = "2026-09-28",
    ) -> dict[str, object]:
        return {
            "category_id": str(category_id or self.transport_id),
            "activity_type": activity_type,
            "quantity": quantity,
            "unit": unit,
            "activity_date": activity_date,
            "notes": "test activity",
        }

    def _create_activity(self, **payload_overrides: object) -> dict[str, object]:
        response = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(**payload_overrides),
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_calculates_and_stores_selected_factor(self) -> None:
        response = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(quantity="2.5"),
        )
        self.assertEqual(response.status_code, 201, response.text)
        body = response.json()
        expected_co2e = Decimal("2.5") * Decimal(body["emission_factor"]["factor_value"])
        self.assertEqual(Decimal(body["calculated_co2e"]), expected_co2e.quantize(Decimal("0.000001")))
        self.assertEqual(body["emission_factor"]["source_year"], 2006)
        self.assertNotIn("DEV ONLY", body["emission_factor"]["source_name"])
        with SessionLocal() as session:
            activity = session.get(
                Activity,
                uuid.UUID(body["id"]),
            )
            factor = session.get(EmissionFactor, activity.emission_factor_id)
            self.assertEqual(factor.activity_type, "car_petrol")

    def test_user_fuel_price_is_persisted_and_used_in_personalized_savings(self) -> None:
        response = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(
                category_id=self.energy_id,
                activity_type="generator_petrol",
                quantity="5",
                unit="L",
            ) | {"unit_cost_ngn": "850"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(Decimal(response.json()["unit_cost_ngn"]), Decimal("850"))

        insights = self.client.get("/insights/fuel", headers=self.headers)
        self.assertEqual(insights.status_code, 200, insights.text)
        fuel = next(
            item for item in insights.json()["fuels"]
            if item["activity_type"] == "generator_petrol"
        )
        self.assertEqual(Decimal(fuel["total_quantity"]), Decimal("5"))
        self.assertEqual(Decimal(fuel["total_cost_ngn"]), Decimal("4250"))
        self.assertEqual(
            Decimal(fuel["total_co2e"]),
            Decimal("5") * Decimal(response.json()["emission_factor"]["factor_value"]),
        )

        updated = self.client.put(
            f"/activities/{response.json()['id']}",
            headers=self.headers,
            json={"unit_cost_ngn": "900"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(Decimal(updated.json()["unit_cost_ngn"]), Decimal("900"))

    def test_create_rejects_invalid_inputs_and_nonactive_factors(self) -> None:
        invalid_category = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(category_id=uuid.uuid4()),
        )
        self.assertEqual(invalid_category.status_code, 422)

        missing_factor = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(activity_type="unconfigured_activity"),
        )
        self.assertEqual(missing_factor.status_code, 422)

        unsupported_unit = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(unit="unsupported_unit"),
        )
        self.assertEqual(unsupported_unit.status_code, 422)

        negative_quantity = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(quantity=-1),
        )
        self.assertEqual(negative_quantity.status_code, 422)

        malformed_date = self.client.post(
            "/activities",
            headers=self.headers,
            json=self._payload(activity_date="not-a-date"),
        )
        self.assertEqual(malformed_date.status_code, 422)

        with SessionLocal() as session:
            factor = session.scalar(
                select(EmissionFactor).where(
                    EmissionFactor.category == "Transport",
                    EmissionFactor.activity_type == "car_petrol",
                    EmissionFactor.factor_unit == "kg_co2e_per_L",
                    EmissionFactor.is_active.is_(True),
                )
            )
            factor_id = factor.id
            factor.is_active = False
            session.commit()
        try:
            inactive_factor = self.client.post(
                "/activities", headers=self.headers, json=self._payload()
            )
            self.assertEqual(inactive_factor.status_code, 409)
        finally:
            with SessionLocal() as session:
                factor = session.get(EmissionFactor, factor_id)
                factor.is_active = True
                session.commit()

    def test_client_cannot_supply_calculation_or_factor_fields(self) -> None:
        response = self.client.post(
            "/activities",
            headers=self.headers,
            json={
                **self._payload(),
                "calculated_co2e": 999999,
                "emission_factor_id": str(uuid.uuid4()),
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_activity_options_returns_active_categories_and_factors(self) -> None:
        response = self.client.get("/activity-options", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIn("Transport", {category["name"] for category in body["categories"]})
        self.assertTrue(
            any(
                factor["activity_type"] == "car_petrol"
                and factor["unit"] == "L"
                and factor["unit_label"] == "Litres (L)"
                for factor in body["emission_factors"]
            )
        )
        electricity = next(
            factor for factor in body["emission_factors"]
            if factor["activity_type"] == "electricity"
        )
        foods = [
            factor for factor in body["emission_factors"]
            if factor["category"] == "Food"
        ]
        self.assertEqual(electricity["unit"], "kWh")
        self.assertEqual(electricity["region"], "Africa average proxy; not Nigeria-specific")
        self.assertGreater(len({factor["factor_value"] for factor in foods}), 1)
        self.assertEqual(
            {category["name"] for category in body["categories"]},
            {"Transport", "Energy", "Food"},
        )

    def test_user_can_create_list_retrieve_update_and_delete(self) -> None:
        created = self._create_activity(quantity=2)
        activity_id = created["id"]

        listed = self.client.get("/activities", headers=self.headers)
        self.assertEqual(listed.status_code, 200)
        self.assertIn(activity_id, {activity["id"] for activity in listed.json()})

        retrieved = self.client.get(f"/activities/{activity_id}", headers=self.headers)
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json()["id"], activity_id)

        updated = self.client.put(
            f"/activities/{activity_id}",
            headers=self.headers,
            json={"quantity": 3, "notes": "updated"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(Decimal(updated.json()["calculated_co2e"]), Decimal("6.858000"))
        self.assertEqual(updated.json()["notes"], "updated")
        self.assertEqual(
            updated.json()["emission_factor"]["id"], created["emission_factor"]["id"]
        )

        changed_factor = self.client.put(
            f"/activities/{activity_id}",
            headers=self.headers,
            json={
                "category_id": str(self.energy_id),
                "activity_type": "electricity",
                "unit": "kWh",
            },
        )
        self.assertEqual(changed_factor.status_code, 200, changed_factor.text)
        self.assertEqual(changed_factor.json()["unit"], "kWh")
        self.assertNotEqual(
            changed_factor.json()["emission_factor"]["id"],
            created["emission_factor"]["id"],
        )

        deleted = self.client.delete(f"/activities/{activity_id}", headers=self.headers)
        self.assertEqual(deleted.status_code, 204)
        missing = self.client.get(f"/activities/{activity_id}", headers=self.headers)
        self.assertEqual(missing.status_code, 404)

    def test_users_cannot_read_update_or_delete_another_users_activity(self) -> None:
        owner_id = self._create_user()
        owner_headers = {"Authorization": f"Bearer {create_access_token(owner_id)}"}
        created = self.client.post(
            "/activities", headers=owner_headers, json=self._payload()
        )
        self.assertEqual(created.status_code, 201, created.text)
        activity_id = created.json()["id"]

        self.assertEqual(
            self.client.get("/activities", headers=self.headers).json(), []
        )
        self.assertEqual(
            self.client.get(f"/activities/{activity_id}", headers=self.headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.put(
                f"/activities/{activity_id}",
                headers=self.headers,
                json={"notes": "forbidden"},
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.delete(f"/activities/{activity_id}", headers=self.headers).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/activities/{activity_id}", headers=owner_headers).status_code,
            200,
        )

    def test_factor_relevant_updates_recalculate_and_forbidden_updates_reject(self) -> None:
        created = self._create_activity(quantity=2)
        activity_id = created["id"]

        forbidden = self.client.put(
            f"/activities/{activity_id}",
            headers=self.headers,
            json={"calculated_co2e": 0, "emission_factor_id": str(uuid.uuid4())},
        )
        self.assertEqual(forbidden.status_code, 422)

        unsupported = self.client.put(
            f"/activities/{activity_id}",
            headers=self.headers,
            json={"unit": "unsupported_unit"},
        )
        self.assertEqual(unsupported.status_code, 422)
        unchanged = self.client.get(f"/activities/{activity_id}", headers=self.headers)
        self.assertEqual(Decimal(unchanged.json()["calculated_co2e"]), Decimal("4.572000"))

    def test_filters_date_range_pagination_and_malformed_dates(self) -> None:
        first = self._create_activity(activity_date="2026-09-28")
        second = self._create_activity(activity_date="2026-09-27")
        third = self._create_activity(
            category_id=self.food_id,
            activity_type="beef",
            unit="kg",
            activity_date="2026-09-26",
        )

        category_filter = self.client.get(
            "/activities", headers=self.headers, params={"category_id": str(self.food_id)}
        )
        self.assertEqual([row["id"] for row in category_filter.json()], [third["id"]])

        type_filter = self.client.get(
            "/activities", headers=self.headers, params={"activity_type": "car_petrol"}
        )
        self.assertEqual(
            {row["id"] for row in type_filter.json()}, {first["id"], second["id"]}
        )

        date_filter = self.client.get(
            "/activities",
            headers=self.headers,
            params={"start_date": "2026-09-27", "end_date": "2026-09-28"},
        )
        self.assertEqual(
            {row["id"] for row in date_filter.json()}, {first["id"], second["id"]}
        )

        paged = self.client.get(
            "/activities", headers=self.headers, params={"limit": 1, "skip": 1}
        )
        self.assertEqual(len(paged.json()), 1)
        self.assertEqual(paged.json()[0]["id"], second["id"])

        malformed_date = self.client.get(
            "/activities", headers=self.headers, params={"start_date": "bad-date"}
        )
        self.assertEqual(malformed_date.status_code, 422)
        reversed_range = self.client.get(
            "/activities",
            headers=self.headers,
            params={"start_date": "2026-09-28", "end_date": "2026-09-27"},
        )
        self.assertEqual(reversed_range.status_code, 422)

    def test_access_token_dependency_and_openapi_documentation(self) -> None:
        no_user = self.client.get("/activities")
        self.assertEqual(no_user.status_code, 401)
        invalid_user = self.client.get(
            "/activities", headers={"Authorization": "Bearer invalid-token"}
        )
        self.assertEqual(invalid_user.status_code, 401)

        openapi = app.openapi()
        self.assertIn("post", openapi["paths"]["/activities"])
        self.assertIn("get", openapi["paths"]["/activities"])
        self.assertIn("422", openapi["paths"]["/activities"]["post"]["responses"])
        self.assertIn("401", openapi["paths"]["/activities"]["post"]["responses"])
        self.assertIn("put", openapi["paths"]["/activities/{activity_id}"])
        self.assertIn("delete", openapi["paths"]["/activities/{activity_id}"])
        self.assertIn("ActivityCreate", openapi["components"]["schemas"])
        self.assertIn("ActivityResponse", openapi["components"]["schemas"])
        self.assertNotIn("X-Dev-User-Id", str(openapi))
        self.assertIn("AccessToken", openapi["components"]["securitySchemes"])


if __name__ == "__main__":
    unittest.main()