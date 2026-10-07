from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


class NigeriaHouseholdActivityOptionsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.user_id = uuid.uuid4()
        with SessionLocal() as session:
            session.add(
                User(
                    id=self.user_id,
                    email=f"{self.user_id}@example.com",
                    password_hash="test-hash",
                    first_name="Test",
                    last_name="Member",
                )
            )
            session.commit()
        self.client.headers.update(
            {"Authorization": f"Bearer {create_access_token(self.user_id)}"}
        )

    def tearDown(self) -> None:
        with SessionLocal() as session:
            session.execute(delete(User).where(User.id == self.user_id))
            session.commit()
        self.client.close()

    def test_fuel_activities_have_local_labels_units_and_transparent_scope(self) -> None:
        response = self.client.get("/activity-options")
        self.assertEqual(response.status_code, 200, response.text)
        factors = {
            item["activity_type"]: item
            for item in response.json()["emission_factors"]
        }

        expected = {
            "generator_petrol": ("Petrol used in a generator", "L", "Litres (L)"),
            "generator_diesel": ("Diesel used in a generator", "L", "Litres (L)"),
            "cooking_lpg": ("LPG used for cooking", "kg", "Kilograms (kg)"),
            "cooking_kerosene": ("Kerosene used for cooking", "L", "Litres (L)"),
        }
        for activity_type, (label, unit, unit_label) in expected.items():
            with self.subTest(activity_type=activity_type):
                factor = factors[activity_type]
                self.assertEqual(factor["category"], "Energy")
                self.assertEqual(factor["activity_label"], label)
                self.assertEqual(factor["unit"], unit)
                self.assertEqual(factor["unit_label"], unit_label)
                self.assertIn("direct combustion only", factor["region"])
                self.assertTrue(factor["source_url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
