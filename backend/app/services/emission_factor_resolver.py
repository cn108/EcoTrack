from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.emission_factor import EmissionFactor


class EmissionFactorResolutionError(Exception):
    pass


class EmissionFactorNotFoundError(EmissionFactorResolutionError):
    pass


class InactiveEmissionFactorError(EmissionFactorResolutionError):
    pass


class AmbiguousEmissionFactorError(EmissionFactorResolutionError):
    pass


class UnsupportedActivityUnitError(EmissionFactorResolutionError):
    pass


def resolve_emission_factor(
    session: Session,
    category: Category,
    activity_type: str,
    unit: str,
) -> EmissionFactor:
    factors = session.scalars(
        select(EmissionFactor).where(
            EmissionFactor.category == category.name,
            EmissionFactor.activity_type == activity_type,
        )
    ).all()
    if not factors:
        raise EmissionFactorNotFoundError(
            "No emission factor is configured for this category and activity type"
        )

    normalized_unit = unit.strip().casefold()
    compatible = [
        factor
        for factor in factors
        if factor.co2e_unit.casefold() == "kg_co2e"
        and factor.factor_unit.casefold() == f"kg_co2e_per_{normalized_unit}"
    ]
    if not compatible:
        raise UnsupportedActivityUnitError(
            "No emission factor supports the requested activity unit"
        )

    active_factors = [factor for factor in compatible if factor.is_active]
    if not active_factors:
        raise InactiveEmissionFactorError(
            "The matching emission factor is inactive"
        )
    if len(active_factors) > 1:
        raise AmbiguousEmissionFactorError(
            "Multiple active emission factors match this activity"
        )
    return active_factors[0]