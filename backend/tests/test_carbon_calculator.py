import unittest
from decimal import Decimal

from app.services.carbon_calculator import calculate_co2e


class CarbonCalculatorTests(unittest.TestCase):
    def test_quantity_times_factor(self) -> None:
        self.assertEqual(
            calculate_co2e(Decimal("12.5"), Decimal("0.4")), Decimal("5.000000")
        )

    def test_decimal_precision_is_preserved_until_rounding(self) -> None:
        self.assertEqual(
            calculate_co2e(Decimal("0.123456"), Decimal("0.1234567890")),
            Decimal("0.015241"),
        )

    def test_zero_quantity(self) -> None:
        self.assertEqual(
            calculate_co2e(Decimal("0"), Decimal("12.5")), Decimal("0.000000")
        )

    def test_negative_quantity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "quantity"):
            calculate_co2e(Decimal("-1"), Decimal("0.5"))

    def test_negative_factor_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "factor"):
            calculate_co2e(Decimal("1"), Decimal("-0.5"))

    def test_half_up_rounding_is_explicit(self) -> None:
        self.assertEqual(
            calculate_co2e(Decimal("1"), Decimal("0.0000005")),
            Decimal("0.000001"),
        )

    def test_float_inputs_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            calculate_co2e(1.0, Decimal("0.5"))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()