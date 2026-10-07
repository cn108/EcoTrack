from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings, settings


password_hasher = PasswordHash.recommended()
ACCESS_TOKEN_ISSUER = "ecotrack-api"


class InvalidAccessTokenError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: UUID,
    *,
    config: Settings = settings,
    expires_delta: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    expiry = now + (expires_delta or timedelta(minutes=config.access_token_expire_minutes))
    return jwt.encode(
        {
            "sub": str(user_id),
            "type": "access",
            "iss": ACCESS_TOKEN_ISSUER,
            "iat": now,
            "exp": expiry,
            "jti": str(uuid4()),
        },
        config.signing_key,
        algorithm="HS256",
    )


def decode_access_token(token: str, *, config: Settings = settings) -> UUID:
    try:
        claims = jwt.decode(
            token,
            config.signing_key,
            algorithms=["HS256"],
            issuer=ACCESS_TOKEN_ISSUER,
            options={"require": ["sub", "type", "iss", "iat", "exp", "jti"]},
        )
        if claims.get("type") != "access":
            raise InvalidAccessTokenError("Invalid access token purpose")
        return UUID(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        raise InvalidAccessTokenError("Invalid or expired access token") from error