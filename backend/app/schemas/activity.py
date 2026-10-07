from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    category_id: UUID
    activity_type: str = Field(min_length=1, max_length=100)
    quantity: Decimal = Field(
        ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False
    )
    unit: str = Field(min_length=1, max_length=64)
    activity_date: date
    unit_cost_ngn: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False
    )
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("category_id", mode="before")
    @classmethod
    def parse_category_id(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError as error:
                raise ValueError("category_id must be a valid UUID") from error
        return value

    @field_validator("activity_date", mode="before")
    @classmethod
    def parse_activity_date(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("activity_date must be an ISO date") from error
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity(cls, value: object) -> Decimal:
        if isinstance(value, bool):
            raise ValueError("quantity must be a decimal number")
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
                raise ValueError("quantity must be a decimal number") from error
        else:
            raise ValueError("quantity must be a decimal number")
        if not result.is_finite():
            raise ValueError("quantity must be finite")
        return result

    @field_validator("unit_cost_ngn", mode="before")
    @classmethod
    def parse_unit_cost(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return ActivityCreate.parse_quantity(value)


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    category_id: UUID | None = None
    activity_type: str | None = Field(default=None, min_length=1, max_length=100)
    quantity: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False
    )
    unit: str | None = Field(default=None, min_length=1, max_length=64)
    activity_date: date | None = None
    unit_cost_ngn: Decimal | None = Field(
        default=None, ge=0, max_digits=20, decimal_places=6, allow_inf_nan=False
    )
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("category_id", mode="before")
    @classmethod
    def parse_category_id(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError as error:
                raise ValueError("category_id must be a valid UUID") from error
        return value

    @field_validator("activity_date", mode="before")
    @classmethod
    def parse_activity_date(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("activity_date must be an ISO date") from error
        return value

    @field_validator("quantity", mode="before")
    @classmethod
    def parse_quantity(cls, value: object) -> object:
        if value is None:
            return None
        return ActivityCreate.parse_quantity(value)

    @field_validator("unit_cost_ngn", mode="before")
    @classmethod
    def parse_unit_cost(cls, value: object) -> Decimal | None:
        if value is None:
            return None
        return ActivityCreate.parse_quantity(value)

    @model_validator(mode="after")
    def validate_update_fields(self) -> ActivityUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one editable field must be provided")
        for field_name in (
            "category_id",
            "activity_type",
            "quantity",
            "unit",
            "activity_date",
        ):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    id: UUID
    name: str


class EmissionFactorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    id: UUID
    factor_value: Decimal
    factor_unit: str
    co2e_unit: str
    source_name: str
    source_url: str | None
    source_year: int
    region: str | None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, strict=True)

    id: UUID
    category: CategoryResponse
    activity_type: str
    quantity: Decimal
    unit: str
    activity_date: date
    calculated_co2e: Decimal
    unit_cost_ngn: Decimal | None
    emission_factor: EmissionFactorResponse
    notes: str | None
    created_at: datetime
    updated_at: datetime