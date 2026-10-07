import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def register_user(
    session: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
) -> User:
    normalized_email = email.strip().lower()
    existing_user = session.scalar(
        select(User.id).where(func.lower(User.email) == normalized_email)
    )
    if existing_user is not None:
        raise EmailAlreadyRegisteredError

    user = User(
        email=normalized_email,
        password_hash=hash_password(password),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
    )
    session.add(user)
    return user


def authenticate_user(session: Session, *, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    user = session.scalar(
        select(User).where(func.lower(User.email) == normalized_email)
    )
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveAccountError
    return user


def create_token_pair(
    session: Session, user: User, *, config: Settings = settings
) -> TokenPair:
    refresh_token = f"rt_{secrets.token_urlsafe(48)}"
    expires_at = datetime.now(UTC) + timedelta(days=config.refresh_token_expire_days)
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
        )
    )
    return TokenPair(
        access_token=create_access_token(user.id, config=config),
        refresh_token=refresh_token,
    )


def rotate_refresh_token(
    session: Session, token: str, *, config: Settings = settings
) -> tuple[User, TokenPair]:
    if not token.startswith("rt_"):
        raise InvalidRefreshTokenError
    token_record = session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(token))
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        token_record is None
        or token_record.revoked_at is not None
        or token_record.expires_at <= now
    ):
        raise InvalidRefreshTokenError

    user = session.get(User, token_record.user_id)
    if user is None or not user.is_active:
        raise InactiveAccountError

    token_record.revoked_at = now
    return user, create_token_pair(session, user, config=config)


def revoke_refresh_token(session: Session, token: str) -> bool:
    if not token.startswith("rt_"):
        return False
    token_record = session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(token))
        .with_for_update()
    )
    if token_record is None or token_record.revoked_at is not None:
        return False
    token_record.revoked_at = datetime.now(UTC)
    return True