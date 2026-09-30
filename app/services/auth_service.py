from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.config.config import security_config
from app.core.exception import AuthenticationError, ConflictError
from app.models.auth import UserRole, public_user
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password


def register_user(users: UserRepository, email: str, password: str) -> dict[str, Any]:
    normalized_email = email.lower()
    now = datetime.now(timezone.utc)
    role = UserRole.ADMIN if normalized_email in security_config["ADMIN_EMAILS"] else UserRole.USER
    document = {"email": normalized_email, "password_hash": hash_password(password), "role": role.value, "is_active": True, "created_at": now, "updated_at": now}
    try:
        return public_user(users.create(document))
    except DuplicateKeyError as error:
        raise ConflictError from error


def authenticate(users: UserRepository, refresh_tokens: RefreshTokenRepository, email: str, password: str) -> dict[str, Any]:
    user = users.find_by_email(email.lower())
    if not user or not user.get("is_active") or not verify_password(password, user["password_hash"]):
        raise AuthenticationError
    access, expires_in = create_access_token(str(user["_id"]), user["role"])
    refresh, refresh_expires = create_refresh_token(str(user["_id"]), user["role"])
    refresh_tokens.create({"token_hash": hash_token(refresh), "user_id": user["_id"], "expires_at": refresh_expires, "created_at": datetime.now(timezone.utc), "revoked_at": None})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": expires_in, "user": public_user(user)}
