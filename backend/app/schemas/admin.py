from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class AdminUserSummary(BaseModel):
    model_config = ConfigDict(strict=True)

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    country: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime
    activity_count: int
    total_co2e: Decimal
    last_activity_date: date | None


class AdminUsersPage(BaseModel):
    model_config = ConfigDict(strict=True)

    items: list[AdminUserSummary]
    total: int
    skip: int
    limit: int


class AdminUserActivity(BaseModel):
    model_config = ConfigDict(strict=True)

    id: UUID
    category: str
    activity_type: str
    quantity: Decimal
    unit: str
    activity_date: date
    calculated_co2e: Decimal
    factor_value: Decimal
    factor_unit: str
    source_name: str
    source_url: str | None
    source_year: int
    region: str | None


class AdminUserActivitiesPage(BaseModel):
    model_config = ConfigDict(strict=True)

    user_id: UUID
    items: list[AdminUserActivity]
    total: int
    skip: int
    limit: int
