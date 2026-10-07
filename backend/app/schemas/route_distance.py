from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RouteDistanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

    origin: str = Field(min_length=2, max_length=200)
    destination: str = Field(min_length=2, max_length=200)

    @model_validator(mode="after")
    def locations_must_differ(self) -> RouteDistanceRequest:
        if self.origin.casefold() == self.destination.casefold():
            raise ValueError("Origin and destination must be different")
        return self


class RouteDistanceResponse(BaseModel):
    distance_meters: int = Field(ge=0)
    distance_km: float = Field(ge=0, allow_inf_nan=False)
    duration_seconds: float = Field(ge=0, allow_inf_nan=False)
