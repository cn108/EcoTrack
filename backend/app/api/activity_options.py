from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.category import Category
from app.models.emission_factor import EmissionFactor
from app.models.user import User
from app.schemas.activity_options import (
    ActivityCategoryOption,
    ActivityOptionsResponse,
    EmissionFactorOption,
)


router = APIRouter(tags=["activity-options"])

ACTIVITY_LABELS = {
    "car_petrol": "Petrol burned",
    "car_diesel": "Diesel burned",
    "generator_petrol": "Petrol used in a generator",
    "generator_diesel": "Diesel used in a generator",
    "cooking_lpg": "LPG used for cooking",
    "cooking_kerosene": "Kerosene used for cooking",
    "beef": "Beef (beef herd)",
    "beef_dairy": "Beef (dairy herd)",
    "lamb_mutton": "Lamb and mutton",
    "poultry": "Poultry",
    "farmed_fish": "Farmed fish",
    "pulses": "Pulses",
}
UNIT_LABELS = {
    "l": "Litres (L)",
    "kwh": "Kilowatt-hours (kWh)",
    "kg": "Kilograms (kg)",
}


@router.get(
    "/activity-options",
    response_model=ActivityOptionsResponse,
    summary="Get categories and active activity factor options",
    description="Provides valid category, activity-type, and unit combinations for activity entry.",
)
def get_activity_options(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityOptionsResponse:
    del current_user
    categories = session.scalars(
        select(Category).where(Category.is_active.is_(True)).order_by(Category.name)
    ).all()
    factors = session.scalars(
        select(EmissionFactor)
        .where(EmissionFactor.is_active.is_(True))
        .order_by(EmissionFactor.category, EmissionFactor.activity_type, EmissionFactor.id)
    ).all()
    available_categories = {factor.category for factor in factors}
    categories = [category for category in categories if category.name in available_categories]
    factor_options = []
    for factor in factors:
        prefix = f"{factor.co2e_unit}_per_"
        unit = (
            factor.factor_unit[len(prefix) :]
            if factor.factor_unit.casefold().startswith(prefix.casefold())
            else factor.factor_unit
        )
        factor_options.append(
            EmissionFactorOption(
                id=factor.id,
                category=factor.category,
                activity_type=factor.activity_type,
                activity_label=ACTIVITY_LABELS.get(
                    factor.activity_type,
                    factor.activity_type.replace("_", " ").capitalize(),
                ),
                unit=unit,
                unit_label=UNIT_LABELS.get(unit.casefold(), unit),
                factor_value=factor.factor_value,
                co2e_unit=factor.co2e_unit,
                source_name=factor.source_name,
                source_url=factor.source_url,
                source_year=factor.source_year,
                region=factor.region,
            )
        )
    return ActivityOptionsResponse(
        categories=[ActivityCategoryOption.model_validate(item) for item in categories],
        emission_factors=factor_options,
    )