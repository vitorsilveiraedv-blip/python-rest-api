"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from service_desk_api.api.dependencies import get_current_user
from service_desk_api.config import get_settings
from service_desk_api.database import get_db
from service_desk_api.models.user import User
from service_desk_api.schemas.auth import (
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserRead,
    UserRegister,
)
from service_desk_api.security import create_access_token
from service_desk_api.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)
from service_desk_api.services.auth_sessions import (
    InvalidRefreshTokenError,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)
from service_desk_api.services.login_rate_limit import (
    LoginRateLimitExceeded,
    check_login_rate_limit,
    clear_email_failures,
    record_failed_login,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a requester account",
)
def register(
    payload: UserRegister,
    db: Annotated[Session, Depends(get_db)],
) -> User:
    try:
        return register_user(
            db,
            email=str(payload.email),
            full_name=payload.full_name,
            password=payload.password,
        )
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from None


@router.post("/login", response_model=TokenResponse, summary="Obtain access and refresh tokens")
def login(
    payload: UserLogin,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    email = str(payload.email)
    client_ip = request.client.host if request.client else "unknown"
    try:
        check_login_rate_limit(db, email=email, client_ip=client_ip)
    except LoginRateLimitExceeded as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(error.retry_after)},
        ) from None

    try:
        user = authenticate_user(db, email=email, password=payload.password)
    except InvalidCredentialsError:
        record_failed_login(db, email=email, client_ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    clear_email_failures(db, email=email)
    settings = get_settings()
    refresh_token = create_refresh_session(db, user)
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenResponse, summary="Rotate a refresh token")
def refresh(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    try:
        user, refresh_token = rotate_refresh_session(db, payload.refresh_token)
    except InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user),
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh session")
def logout(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    revoke_refresh_session(db, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead, summary="Get the authenticated user")
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
