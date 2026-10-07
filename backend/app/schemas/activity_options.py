from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityCategoryOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class EmissionFactorOption(BaseModel):
    id: UUID
    category: str
    activity_type: str
    activity_label: str
    unit: str
    unit_label: str
    factor_value: Decimal
    co2e_unit: str
    source_name: str
    source_url: str | None
    source_year: int
    region: str | None


class ActivityOptionsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    categories: list[ActivityCategoryOption]
    emission_factors: list[EmissionFactorOption]