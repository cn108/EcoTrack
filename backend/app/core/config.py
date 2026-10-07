from __future__ import annotations

import secrets
from typing import Literal

from pydantic import EmailStr, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://ecotrack:ecotrack@localhost:5432/ecotrack"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: SecretStr | None = None
    admin_email: EmailStr | None = None
    refresh_cookie_path: str = Field(
        default="/auth",
        pattern=r"^/[A-Za-z0-9/_-]*$",
    )
    osm_nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    osm_routing_url: str = "https://router.project-osrm.org/route/v1/driving"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @model_validator(mode="after")
    def validate_secrets(self) -> Settings:
        if self.secret_key is None:
            if self.environment == "production":
                raise ValueError("SECRET_KEY is required in production")
            self.secret_key = SecretStr(secrets.token_urlsafe(48))
        elif len(self.secret_key.get_secret_value()) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters")
        if self.access_token_expire_minutes < 1:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        if self.refresh_token_expire_days < 1:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be positive")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.environment == "production"

    @property
    def signing_key(self) -> str:
        assert self.secret_key is not None
        return self.secret_key.get_secret_value()


settings = Settings()