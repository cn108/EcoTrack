from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.activity import ActivityResponse


class CategoryEmissionResponse(BaseModel):
    category_id: UUID
    category_name: str
    total_co2e: Decimal
    activity_count: int


class MonthlyEmissionResponse(BaseModel):
    month: str
    total_co2e: Decimal
    activity_count: int


class ActivityTypeEmissionResponse(BaseModel):
    activity_type: str
    total_co2e: Decimal
    activity_count: int


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_month_total_co2e: Decimal
    previous_month_total_co2e: Decimal
    percentage_change_percent: Decimal | None
    daily_average_co2e: Decimal
    activities_this_month: int
    highest_emission_category: CategoryEmissionResponse | None
    highest_emission_activity_type: ActivityTypeEmissionResponse | None
    category_totals: list[CategoryEmissionResponse]
    recent_activities: list[ActivityResponse]