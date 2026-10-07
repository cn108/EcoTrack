import unittest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from app.schemas.activity import ActivityCreate, ActivityUpdate


class ActivitySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = {
            "category_id": str(uuid4()),
            "activity_type": " car_petrol ",
            "quantity": 1.25,
            "unit": " test_unit ",
            "activity_date": "2026-09-28",
        }

    def test_create_parses_wire_values_strictly(self) -> None:
        request = ActivityCreate.model_validate(self.payload)
        self.assertEqual(request.quantity, Decimal("1.25"))
        self.assertEqual(request.activity_date, date(2026, 9, 28))
        self.assertEqual(request.activity_type, "car_petrol")
        self.assertEqual(request.unit, "test_unit")

    def test_negative_quantity_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            ActivityCreate.model_validate({**self.payload, "quantity": -1})

    def test_client_cannot_supply_authoritative_or_protected_fields(self) -> None:
        for field_name in ("calculated_co2e", "emission_factor_id", "user_id"):
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValidationError):
                    ActivityCreate.model_validate({**self.payload, field_name: "forged"})

    def test_update_must_include_editable_fields(self) -> None:
        with self.assertRaises(ValidationError):
            ActivityUpdate.model_validate({})
        with self.assertRaises(ValidationError):
            ActivityUpdate.model_validate({"activity_type": None})


if __name__ == "__main__":
    unittest.main()