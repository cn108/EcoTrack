import os
import unittest
from decimal import Decimal
from unittest.mock import Mock

os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

from app.models.category import Category
from app.models.emission_factor import EmissionFactor
from app.services.emission_factor_resolver import (
    AmbiguousEmissionFactorError,
    EmissionFactorNotFoundError,
    InactiveEmissionFactorError,
    UnsupportedActivityUnitError,
    resolve_emission_factor,
)


def make_factor(*, active: bool = True, unit: str = "kg_co2e_per_mile") -> EmissionFactor:
    return EmissionFactor(
        category="Transport",
        activity_type="car_petrol",
        factor_value=Decimal("0.5"),
        factor_unit=unit,
        co2e_unit="kg_co2e",
        source_name="test factor",
        source_year=2026,
        is_active=active,
    )


class EmissionFactorResolverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = Mock()
        self.category = Category(name="Transport")

    def resolve(self) -> EmissionFactor:
        return resolve_emission_factor(self.session, self.category, "car_petrol", "mile")

    def set_factors(self, factors: list[EmissionFactor]) -> None:
        self.session.scalars.return_value.all.return_value = factors

    def test_returns_single_active_unit_match(self) -> None:
        factor = make_factor()
        self.set_factors([factor])
        self.assertIs(self.resolve(), factor)

    def test_missing_factor_is_rejected(self) -> None:
        self.set_factors([])
        with self.assertRaises(EmissionFactorNotFoundError):
            self.resolve()

    def test_inactive_factor_is_rejected(self) -> None:
        self.set_factors([make_factor(active=False)])
        with self.assertRaises(InactiveEmissionFactorError):
            self.resolve()

    def test_unsupported_unit_is_rejected(self) -> None:
        self.set_factors([make_factor(unit="kg_co2e_per_kilometer")])
        with self.assertRaises(UnsupportedActivityUnitError):
            self.resolve()

    def test_multiple_active_matches_are_rejected_as_ambiguous(self) -> None:
        self.set_factors([make_factor(), make_factor()])
        with self.assertRaises(AmbiguousEmissionFactorError):
            self.resolve()


if __name__ == "__main__":
    unittest.main()