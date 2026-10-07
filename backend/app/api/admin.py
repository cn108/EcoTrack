from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.admin import (
    AdminUserActivitiesPage,
    AdminUserActivity,
    AdminUsersPage,
    AdminUserSummary,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    configured_email = settings.admin_email
    if configured_email is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not configured",
        )
    if (
        current_user.email.casefold() != str(configured_email).casefold()
        or not current_user.is_verified
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is not permitted",
        )
    return current_user


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.get(
    "/users",
    response_model=AdminUsersPage,
    summary="Search user accounts and activity summaries",
)
def list_users(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    is_active: bool | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUsersPage:
    if created_from is not None and created_to is not None and created_from > created_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="created_from must not be after created_to",
        )

    conditions = []
    if is_active is not None:
        conditions.append(User.is_active.is_(is_active))
    if created_from is not None:
        conditions.append(User.created_at >= datetime.combine(created_from, time.min))
    if created_to is not None:
        conditions.append(User.created_at <= datetime.combine(created_to, time.max))
    if search is not None:
        search_term = search.strip()
        if not search_term:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="search must contain a non-whitespace character",
            )
        pattern = f"%{_escape_like(search_term)}%"
        conditions.append(
            or_(
                User.email.ilike(pattern, escape="\\"),
                User.first_name.ilike(pattern, escape="\\"),
                User.last_name.ilike(pattern, escape="\\"),
            )
        )

    total = session.scalar(
        select(func.count()).select_from(User).where(*conditions)
    ) or 0
    rows = session.execute(
        select(
            User,
            func.count(Activity.id).label("activity_count"),
            func.coalesce(func.sum(Activity.calculated_co2e), Decimal("0")).label("total_co2e"),
            func.max(Activity.activity_date).label("last_activity_date"),
        )
        .outerjoin(Activity, Activity.user_id == User.id)
        .where(*conditions)
        .group_by(User.id)
        .order_by(User.created_at.desc(), User.id)
        .offset(skip)
        .limit(limit)
    ).all()
    logger.info(
        "admin_user_search",
        extra={
            "admin_user_id": str(current_admin.id),
            "result_count": len(rows),
            "offset": skip,
            "page_size": limit,
        },
    )
    return AdminUsersPage(
        items=[
            AdminUserSummary(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                country=user.country,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                activity_count=activity_count,
                total_co2e=total_co2e,
                last_activity_date=last_activity_date,
            )
            for user, activity_count, total_co2e, last_activity_date in rows
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/users/{user_id}/activities",
    response_model=AdminUserActivitiesPage,
    summary="Filter a user's recorded activity",
    description=(
        "Returns activity quantities, dates, emissions, and factor provenance. "
        "Private notes and user-entered fuel prices are intentionally excluded."
    ),
)
def list_user_activities(
    user_id: UUID,
    activity_type: str | None = Query(default=None, min_length=1, max_length=100),
    category: str | None = Query(default=None, min_length=1, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
) -> AdminUserActivitiesPage:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must not be after date_to",
        )
    if session.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    conditions = [Activity.user_id == user_id]
    if activity_type is not None:
        conditions.append(Activity.activity_type == activity_type)
    if category is not None:
        conditions.append(Activity.category.has(name=category))
    if date_from is not None:
        conditions.append(Activity.activity_date >= date_from)
    if date_to is not None:
        conditions.append(Activity.activity_date <= date_to)

    total = session.scalar(
        select(func.count()).select_from(Activity).where(*conditions)
    ) or 0
    activities = session.scalars(
        select(Activity)
        .options(joinedload(Activity.category), joinedload(Activity.emission_factor))
        .where(*conditions)
        .order_by(Activity.activity_date.desc(), Activity.created_at.desc(), Activity.id)
        .offset(skip)
        .limit(limit)
    ).all()
    logger.info(
        "admin_user_activities_viewed",
        extra={
            "admin_user_id": str(current_admin.id),
            "target_user_id": str(user_id),
            "result_count": len(activities),
            "offset": skip,
            "page_size": limit,
        },
    )
    return AdminUserActivitiesPage(
        user_id=user_id,
        items=[
            AdminUserActivity(
                id=activity.id,
                category=activity.category.name,
                activity_type=activity.activity_type,
                quantity=activity.quantity,
                unit=activity.unit,
                activity_date=activity.activity_date,
                calculated_co2e=activity.calculated_co2e,
                factor_value=activity.emission_factor.factor_value,
                factor_unit=activity.emission_factor.factor_unit,
                source_name=activity.emission_factor.source_name,
                source_url=activity.emission_factor.source_url,
                source_year=activity.emission_factor.source_year,
                region=activity.emission_factor.region,
            )
            for activity in activities
        ],
        total=total,
        skip=skip,
        limit=limit,
    )
