from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class GoalCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    target_type: str = Field(min_length=1, max_length=100)
    baseline_co2e: Decimal = Field(ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    target_co2e: Decimal = Field(ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    start_date: date
    end_date: date

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date(cls, value: object) -> date:
        if isinstance(value, datetime):
            raise ValueError("Dates must use YYYY-MM-DD format")
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("Dates must use YYYY-MM-DD format") from error
            if parsed.isoformat() != value:
                raise ValueError("Dates must use YYYY-MM-DD format")
            return parsed
        raise ValueError("Dates must use YYYY-MM-DD format")

    @field_validator("baseline_co2e", "target_co2e", mode="before")
    @classmethod
    def parse_decimal(cls, value: object) -> Decimal:
        if isinstance(value, bool):
            raise ValueError("CO₂e values must be numbers")
        if isinstance(value, Decimal):
            result = value
        elif isinstance(value, int):
            result = Decimal(value)
        elif isinstance(value, float):
            result = Decimal(str(value))
        elif isinstance(value, str):
            try:
                result = Decimal(value)
            except InvalidOperation as error:
                raise ValueError("CO₂e values must be valid decimals") from error
        else:
            raise ValueError("CO₂e values must be numbers")
        if not result.is_finite():
            raise ValueError("CO₂e values must be finite")
        return result

    @model_validator(mode="after")
    def validate_date_range(self) -> GoalCreate:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        return self


class GoalUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    target_type: str | None = Field(default=None, min_length=1, max_length=100)
    baseline_co2e: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    target_co2e: Decimal | None = Field(default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False)
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_date(cls, value: object) -> date | None:
        if value is None:
            return None
        return GoalCreate.parse_date(value)

    @field_validator("baseline_co2e", "target_co2e", mode="before")
    @classmethod
    def parse_decimal(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return GoalCreate.parse_decimal(value)

    @model_validator(mode="after")
    def validate_update_fields(self) -> GoalUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one editable field must be provided")
        for field_name in ("name", "target_type", "baseline_co2e", "target_co2e"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        if "start_date" in self.model_fields_set and self.start_date is None:
            raise ValueError("start_date cannot be null")
        if "end_date" in self.model_fields_set and self.end_date is None:
            raise ValueError("end_date cannot be null")
        start_date = self.start_date if "start_date" in self.model_fields_set else None
        end_date = self.end_date if "end_date" in self.model_fields_set else None
        if start_date is not None and end_date is not None and start_date > end_date:
            raise ValueError("start_date must not be after end_date")
        return self


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    id: UUID
    name: str
    target_type: str
    baseline_co2e: Decimal
    target_co2e: Decimal
    start_date: date
    end_date: date
    is_completed: bool
    current_co2e: Decimal
    progress_percent: Decimal
    remaining_co2e: Decimal
    created_at: datetime
    updated_at: datetime
