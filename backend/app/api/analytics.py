from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.activity import ActivityResponse
from app.schemas.analytics import (
    ActivityTypeEmissionResponse,
    CategoryEmissionResponse,
    DashboardResponse,
    MonthlyEmissionResponse,
)
from app.services.analytics import (
    get_activity_type_emissions,
    get_category_emissions,
    get_dashboard_snapshot,
    get_monthly_emissions,
    month_start,
    utc_today,
)


router = APIRouter(tags=["analytics"])


def _date_range(
    start_date: date | None,
    end_date: date | None,
    *,
    defaults_to_last_year: bool,
) -> tuple[date | None, date | None]:
    today = utc_today()
    if defaults_to_last_year:
        end_date = end_date or today
        if start_date is None:
            end_date_month = month_start(end_date)
            start_date = end_date_month
            for _ in range(11):
                start_date = (start_date - timedelta(days=1)).replace(day=1)
    if start_date is not None and end_date is not None:
        if start_date > end_date:
            raise HTTPException(status_code=422, detail="start_date must not be after end_date")
        if (end_date - start_date).days > 366 * 10:
            raise HTTPException(status_code=422, detail="Date range cannot exceed ten years")
    return start_date, end_date


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="Get dashboard totals and recent activity",
    description="Aggregates the authenticated user's current-month and recent activity data.",
)
def dashboard(
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    snapshot = get_dashboard_snapshot(session, current_user.id)
    snapshot["recent_activities"] = [
        ActivityResponse.model_validate(activity)
        for activity in snapshot["recent_activities"]
    ]
    return DashboardResponse.model_validate(snapshot)


@router.get(
    "/analytics/monthly",
    response_model=list[MonthlyEmissionResponse],
    summary="Get monthly CO2e totals",
    description="Returns database-aggregated monthly totals, filling months without activity with zero.",
)
def monthly_analytics(
    start_date: date | None = None,
    end_date: date | None = None,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    start_date, end_date = _date_range(
        start_date, end_date, defaults_to_last_year=True
    )
    return get_monthly_emissions(
        session,
        current_user.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/analytics/categories",
    response_model=list[CategoryEmissionResponse],
    summary="Get emissions grouped by category",
)
def category_analytics(
    start_date: date | None = None,
    end_date: date | None = None,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    start_date, end_date = _date_range(
        start_date, end_date, defaults_to_last_year=False
    )
    return get_category_emissions(
        session, current_user.id, start_date=start_date, end_date=end_date
    )


@router.get(
    "/analytics/activity-types",
    response_model=list[ActivityTypeEmissionResponse],
    summary="Get emissions grouped by activity type",
)
def activity_type_analytics(
    start_date: date | None = None,
    end_date: date | None = None,
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, object]]:
    start_date, end_date = _date_range(
        start_date, end_date, defaults_to_last_year=False
    )
    return get_activity_type_emissions(
        session, current_user.id, start_date=start_date, end_date=end_date
    )