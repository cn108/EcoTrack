from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FuelInsight(BaseModel):
    model_config = ConfigDict(strict=True)

    activity_type: str
    unit: str
    activity_count: int
    total_quantity: Decimal
    total_cost_ngn: Decimal
    total_co2e: Decimal


class FuelInsightsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    fuels: list[FuelInsight]
