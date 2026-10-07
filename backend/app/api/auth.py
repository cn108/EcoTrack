import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegistrationRequest, UserResponse
from app.services.auth import (
    EmailAlreadyRegisteredError,
    InactiveAccountError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    authenticate_user,
    create_token_pair,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
REFRESH_COOKIE_NAME = "ecotrack_refresh"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path=settings.refresh_cookie_path,
    )


def _commit_auth(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        logger.info("authentication_write_conflict")
        raise HTTPException(status_code=409, detail="Account or session conflict") from error
    except SQLAlchemyError as error:
        session.rollback()
        logger.error(
            "authentication_database_error",
            extra={"error_type": type(error).__name__},
        )
        raise HTTPException(status_code=500, detail="Authentication operation failed") from error


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an account",
    responses={409: {"description": "Email is already registered"}},
)
def register(
    payload: RegistrationRequest,
    session: Session = Depends(get_db),
) -> User:
    try:
        user = register_user(
            session,
            email=str(payload.email),
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except EmailAlreadyRegisteredError as error:
        raise HTTPException(status_code=409, detail="Email is already registered") from error

    _commit_auth(session)
    logger.info("user_registered", extra={"user_id": str(user.id)})
    return user


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in and issue an access token",
    description=(
        "Returns a short-lived Bearer access token. The rotated opaque refresh token "
        "is delivered only in an HTTP-only cookie."
    ),
    responses={401: {"description": "Credentials are invalid or account is inactive"}},
)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_db),
) -> AuthResponse:
    try:
        user = authenticate_user(
            session, email=str(payload.email), password=payload.password
        )
    except InvalidCredentialsError as error:
        raise HTTPException(status_code=401, detail="Invalid email or password") from error
    except InactiveAccountError as error:
        raise HTTPException(status_code=401, detail="Account is inactive") from error

    tokens = create_token_pair(session, user)
    _commit_auth(session)
    _set_refresh_cookie(response, tokens.refresh_token)
    logger.info("user_logged_in", extra={"user_id": str(user.id)})
    return AuthResponse(access_token=tokens.access_token, user=UserResponse.model_validate(user))


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Rotate the refresh token",
    responses={401: {"description": "Refresh token is invalid, expired, revoked, or inactive"}},
)
def refresh(
    response: Response,
    session: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> AuthResponse:
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Refresh token is required")
    try:
        user, tokens = rotate_refresh_token(session, refresh_token)
    except (InvalidRefreshTokenError, InactiveAccountError) as error:
        session.rollback()
        raise HTTPException(status_code=401, detail="Refresh token is invalid") from error

    _commit_auth(session)
    _set_refresh_cookie(response, tokens.refresh_token)
    logger.info("refresh_token_rotated", extra={"user_id": str(user.id)})
    return AuthResponse(access_token=tokens.access_token, user=UserResponse.model_validate(user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the current refresh token",
    responses={401: {"description": "No valid refresh token was supplied"}},
)
def logout(
    response: Response,
    session: Session = Depends(get_db),
    refresh_token: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
) -> Response:
    if refresh_token is not None:
        revoke_refresh_token(session, refresh_token)
        _commit_auth(session)
    _clear_refresh_cookie(response)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated account",
    responses={401: {"description": "Access token is missing, invalid, or expired"}},
)
def current_account(current_user: User = Depends(get_current_user)) -> User:
    return current_user