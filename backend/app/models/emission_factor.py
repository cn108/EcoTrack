from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

class EmissionFactor(Base):
    __tablename__ = "emission_factors"
    __table_args__ = (
        CheckConstraint(
            "factor_value >= 0", name="ck_emission_factors_non_negative_value"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_value: Mapped[Decimal] = mapped_column(Numeric(20, 10), nullable=False)
    factor_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    co2e_unit: Mapped[str] = mapped_column(
        String(32), nullable=False, default="kg_co2e", server_default="kg_co2e"
    )
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_year: Mapped[int] = mapped_column(Integer, nullable=False)
    region: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    activities: Mapped[list[Activity]] = relationship(back_populates="emission_factor")