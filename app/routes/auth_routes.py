from fastapi import APIRouter, Depends, status

from app.controllers.auth_controller import (
    current_user_controller,
    login_controller,
    register_user_controller,
    reset_password_controller,
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import current_user, get_refresh_token_repository, get_user_repository
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, ResetPasswordRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, users: UserRepository = Depends(get_user_repository)):
    return register_user_controller(users, payload.email, payload.password)


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    users: UserRepository = Depends(get_user_repository),
    refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository),
):
    return login_controller(users, refresh_tokens, payload.email, payload.password)


@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user)):
    return current_user_controller(user)


@router.post("/reset-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def reset_password(_: ResetPasswordRequest):
    return reset_password_controller()
