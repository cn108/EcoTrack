from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Activity(TimestampMixin, Base):
    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_activities_non_negative_quantity"),
        CheckConstraint(
            "calculated_co2e >= 0", name="ck_activities_non_negative_calculated_co2e"
        ),
        CheckConstraint(
            "unit_cost_ngn IS NULL OR unit_cost_ngn >= 0",
            name="ck_activities_non_negative_unit_cost_ngn",
        ),
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_activity_date", "activity_date"),
        Index("ix_activities_category_id", "category_id"),
        Index("ix_activities_emission_factor_id", "emission_factor_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    emission_factor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("emission_factors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    calculated_co2e: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    unit_cost_ngn: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    notes: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="activities")
    category: Mapped[Category] = relationship(back_populates="activities")
    emission_factor: Mapped[EmissionFactor] = relationship(back_populates="activities")