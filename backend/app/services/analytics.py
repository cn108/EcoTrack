from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.activity import Activity
from app.models.category import Category


CO2E_QUANTUM = Decimal("0.000001")
PERCENT_QUANTUM = Decimal("0.01")


def utc_today() -> date:
    return datetime.now(UTC).date()


def month_start(day: date) -> date:
    return day.replace(day=1)


def previous_month_start(day: date) -> date:
    current_start = month_start(day)
    return (current_start - timedelta(days=1)).replace(day=1)


def next_month_start(day: date) -> date:
    current_start = month_start(day)
    if current_start.month == 12:
        return current_start.replace(year=current_start.year + 1, month=1)
    return current_start.replace(month=current_start.month + 1)


def get_dashboard_snapshot(
    session: Session, user_id: UUID, *, today: date | None = None
) -> dict[str, object]:
    current_day = today or utc_today()
    current_start = month_start(current_day)
    next_start = next_month_start(current_day)
    previous_start = previous_month_start(current_day)

    current_total, activity_count = session.execute(
        select(
            func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0")),
            func.count(Activity.id),
        ).where(
            Activity.user_id == user_id,
            Activity.activity_date >= current_start,
            Activity.activity_date < next_start,
        )
    ).one()
    previous_total = session.scalar(
        select(func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0"))).where(
            Activity.user_id == user_id,
            Activity.activity_date >= previous_start,
            Activity.activity_date < current_start,
        )
    )
    current_total = Decimal(current_total)
    previous_total = Decimal(previous_total)
    percentage_change = (
        ((current_total - previous_total) * Decimal("100") / previous_total).quantize(
            PERCENT_QUANTUM, rounding=ROUND_HALF_UP
        )
        if previous_total != 0
        else None
    )
    daily_average = (current_total / Decimal(current_day.day)).quantize(
        CO2E_QUANTUM, rounding=ROUND_HALF_UP
    )

    category_rows = session.execute(
        select(
            Category.id,
            Category.name,
            func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0")).label(
                "total_co2e"
            ),
            func.count(Activity.id).label("activity_count"),
        )
        .join(Activity, Activity.category_id == Category.id)
        .where(
            Activity.user_id == user_id,
            Activity.activity_date >= current_start,
            Activity.activity_date < next_start,
        )
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Activity.calculated_co2e).desc(), Category.name.asc())
    ).all()
    category_totals = [
        {
            "category_id": row.id,
            "category_name": row.name,
            "total_co2e": Decimal(row.total_co2e),
            "activity_count": row.activity_count,
        }
        for row in category_rows
    ]

    type_rows = session.execute(
        select(
            Activity.activity_type,
            func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0")).label(
                "total_co2e"
            ),
            func.count(Activity.id).label("activity_count"),
        )
        .where(
            Activity.user_id == user_id,
            Activity.activity_date >= current_start,
            Activity.activity_date < next_start,
        )
        .group_by(Activity.activity_type)
        .order_by(func.sum(Activity.calculated_co2e).desc(), Activity.activity_type.asc())
    ).all()
    activity_type_totals = [
        {
            "activity_type": row.activity_type,
            "total_co2e": Decimal(row.total_co2e),
            "activity_count": row.activity_count,
        }
        for row in type_rows
    ]

    recent_activities = list(
        session.scalars(
            select(Activity)
            .options(joinedload(Activity.category), joinedload(Activity.emission_factor))
            .where(Activity.user_id == user_id)
            .order_by(Activity.activity_date.desc(), Activity.created_at.desc())
            .limit(5)
        ).all()
    )

    return {
        "current_month_total_co2e": current_total,
        "previous_month_total_co2e": previous_total,
        "percentage_change_percent": percentage_change,
        "daily_average_co2e": daily_average,
        "activities_this_month": activity_count,
        "highest_emission_category": category_totals[0] if category_totals else None,
        "highest_emission_activity_type": (
            activity_type_totals[0] if activity_type_totals else None
        ),
        "category_totals": category_totals,
        "recent_activities": recent_activities,
    }


def get_monthly_emissions(
    session: Session,
    user_id: UUID,
    *,
    start_date: date,
    end_date: date,
) -> list[dict[str, object]]:
    month_expression = cast(
        func.date_trunc("month", Activity.activity_date), Date
    ).label("month_start")
    rows = session.execute(
        select(
            month_expression,
            func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0")).label(
                "total_co2e"
            ),
            func.count(Activity.id).label("activity_count"),
        )
        .where(
            Activity.user_id == user_id,
            Activity.activity_date >= start_date,
            Activity.activity_date <= end_date,
        )
        .group_by(month_expression)
        .order_by(month_expression)
    ).all()
    totals_by_month = {
        row.month_start.strftime("%Y-%m"): {
            "total_co2e": Decimal(row.total_co2e),
            "activity_count": row.activity_count,
        }
        for row in rows
    }

    results: list[dict[str, object]] = []
    current = month_start(start_date)
    last = month_start(end_date)
    while current <= last:
        key = current.strftime("%Y-%m")
        values = totals_by_month.get(
            key, {"total_co2e": Decimal("0"), "activity_count": 0}
        )
        results.append({"month": key, **values})
        current = next_month_start(current)
    return results


def get_category_emissions(
    session: Session,
    user_id: UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, object]]:
    statement = (
        select(
            Category.id.label("category_id"),
            Category.name.label("category_name"),
            func.sum(Activity.calculated_co2e).label("total_co2e"),
            func.count(Activity.id).label("activity_count"),
        )
        .join(Activity, Activity.category_id == Category.id)
        .where(Activity.user_id == user_id)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Activity.calculated_co2e).desc(), Category.name.asc())
    )
    if start_date is not None:
        statement = statement.where(Activity.activity_date >= start_date)
    if end_date is not None:
        statement = statement.where(Activity.activity_date <= end_date)
    return [dict(row._mapping) for row in session.execute(statement).all()]


def get_activity_type_emissions(
    session: Session,
    user_id: UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, object]]:
    statement = (
        select(
            Activity.activity_type,
            func.sum(Activity.calculated_co2e).label("total_co2e"),
            func.count(Activity.id).label("activity_count"),
        )
        .where(Activity.user_id == user_id)
        .group_by(Activity.activity_type)
        .order_by(func.sum(Activity.calculated_co2e).desc(), Activity.activity_type.asc())
    )
    if start_date is not None:
        statement = statement.where(Activity.activity_date >= start_date)
    if end_date is not None:
        statement = statement.where(Activity.activity_date <= end_date)
    return [dict(row._mapping) for row in session.execute(statement).all()]