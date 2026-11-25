"""Authentication endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from service_desk_api.api.dependencies import get_current_user
from service_desk_api.database import get_db
from service_desk_api.models.user import User
from service_desk_api.schemas.auth import TokenResponse, UserLogin, UserRead, UserRegister
from service_desk_api.security import create_access_token
from service_desk_api.services.auth import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
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


@router.post("/login", response_model=TokenResponse, summary="Obtain an access token")
def login(
    payload: UserLogin,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    try:
        user = authenticate_user(db, email=str(payload.email), password=payload.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    from service_desk_api.config import get_settings

    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(user),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead, summary="Get the authenticated user")
def me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
