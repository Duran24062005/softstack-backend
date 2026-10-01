from fastapi import APIRouter, Depends, Request, Response, status

from app.controllers.auth_controller import (
    current_user_controller,
    login_controller,
    refresh_controller,
    register_user_controller,
    reset_password_controller,
    update_profile_controller,
)
from app.config.config import cookie_config
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.exception import InvalidTokenError
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import current_user, get_refresh_token_repository, get_user_repository
from app.schemas.auth import AuthResponse, LoginRequest, ProfileUpdateRequest, RegisterRequest, ResetPasswordRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, users: UserRepository = Depends(get_user_repository), refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository)):
    register_user_controller(users, payload.email, payload.password, payload.full_name)
    session = login_controller(users, refresh_tokens, payload.email, payload.password)
    set_auth_cookies(response, session["access_token"], session["refresh_token"])
    return {"expires_in": session["expires_in"], "user": session["user"]}


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    response: Response,
    users: UserRepository = Depends(get_user_repository),
    refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository),
):
    session = login_controller(users, refresh_tokens, payload.email, payload.password)
    set_auth_cookies(response, session["access_token"], session["refresh_token"])
    return {"expires_in": session["expires_in"], "user": session["user"]}


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, users: UserRepository = Depends(get_user_repository), refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository)):
    token = request.cookies.get(cookie_config["REFRESH_COOKIE_NAME"])
    if not token:
        raise InvalidTokenError
    session = refresh_controller(users, refresh_tokens, token)
    set_auth_cookies(response, session["access_token"], session["refresh_token"])
    return {"expires_in": session["expires_in"], "user": session["user"]}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository)):
    token = request.cookies.get(cookie_config["REFRESH_COOKIE_NAME"])
    if token:
        from app.core.security import hash_token
        refresh_tokens.revoke(hash_token(token))
    clear_auth_cookies(response)
    return None


@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user)):
    return current_user_controller(user)


@router.patch("/me", response_model=UserResponse)
def update_me(payload: ProfileUpdateRequest, user=Depends(current_user), users: UserRepository = Depends(get_user_repository)):
    return update_profile_controller(users, user, payload)


@router.post("/reset-password", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def reset_password(_: ResetPasswordRequest):
    return reset_password_controller()
