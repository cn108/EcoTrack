from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.insights import FuelInsight, FuelInsightsResponse


router = APIRouter(prefix="/insights", tags=["insights"])
PRICE_TRACKED_FUEL_TYPES = (
    "car_petrol",
    "car_diesel",
    "generator_petrol",
    "generator_diesel",
    "cooking_lpg",
    "cooking_kerosene",
)


@router.get("/fuel", response_model=FuelInsightsResponse, summary="Get personalized fuel spending insights")
def fuel_insights(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FuelInsightsResponse:
    rows = session.execute(
        select(
            Activity.activity_type,
            Activity.unit,
            func.count(Activity.id).label("activity_count"),
            func.sum(Activity.quantity).label("total_quantity"),
            func.sum(Activity.quantity * Activity.unit_cost_ngn).label("total_cost_ngn"),
            func.sum(Activity.calculated_co2e).label("total_co2e"),
        )
        .where(
            Activity.user_id == current_user.id,
            Activity.unit_cost_ngn.is_not(None),
            Activity.activity_type.in_(PRICE_TRACKED_FUEL_TYPES),
        )
        .group_by(Activity.activity_type, Activity.unit)
        .order_by(Activity.activity_type, Activity.unit)
    ).all()
    return FuelInsightsResponse(
        fuels=[
            FuelInsight(
                activity_type=row.activity_type,
                unit=row.unit,
                activity_count=row.activity_count,
                total_quantity=row.total_quantity or Decimal("0"),
                total_cost_ngn=row.total_cost_ngn or Decimal("0"),
                total_co2e=row.total_co2e or Decimal("0"),
            )
            for row in rows
        ]
    )
