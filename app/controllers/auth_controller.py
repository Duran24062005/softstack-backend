from bson import ObjectId
from fastapi.security import HTTPAuthorizationCredentials

from app.core.exception import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    InactiveUserError,
    InvalidTokenError,
    NotImplementedApplicationError,
)
from app.core.security import decode_access_token
from app.models.auth import public_user
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import authenticate, register_user, refresh_session, update_profile


def register_user_controller(users: UserRepository, email: str, password: str, full_name: str):
    try:
        return register_user(users, email, password, full_name)
    except ConflictError:
        raise


def login_controller(users: UserRepository, refresh_tokens: RefreshTokenRepository, email: str, password: str):
    try:
        return authenticate(users, refresh_tokens, email, password)
    except AuthenticationError:
        raise


def refresh_controller(users: UserRepository, refresh_tokens: RefreshTokenRepository, token: str):
    return refresh_session(users, refresh_tokens, token)


def update_profile_controller(users: UserRepository, user, payload):
    return update_profile(users, user, full_name=payload.full_name, email=payload.email, current_password=payload.current_password, new_password=payload.new_password)


def current_user_controller(user):
    return public_user(user)


def reset_password_controller() -> None:
    raise NotImplementedApplicationError


def current_user_auth_controller(credentials: HTTPAuthorizationCredentials | None, users: UserRepository):
    if not credentials:
        raise InvalidTokenError
    try:
        payload = decode_access_token(credentials.credentials)
        user = users.find_by_id(ObjectId(payload["sub"]))
    except Exception as error:
        raise InvalidTokenError from error
    if not user or not user.get("is_active"):
        raise InactiveUserError
    return user


def require_role_controller(user, roles: tuple[str, ...]):
    if user.get("role") not in roles:
        raise AuthorizationError
    return user
