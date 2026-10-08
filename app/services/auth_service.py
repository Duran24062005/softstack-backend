from datetime import datetime, timezone
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.config.config import security_config
from app.core.exception import AuthenticationError, ConflictError, EmailNotVerifiedError, InvalidStudentAcademicProfileError, NotFoundError
from app.models.auth import AccountStatus, UserRole, public_user
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.core.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password
from app.services.account_status_service import ensure_active_account
from app.schemas.student_profile import AcademicProfileInput
from app.services.student_profile_service import serialize_academic_profile


def _create_account(
    users: UserRepository,
    email: str,
    password: str,
    full_name: str,
    *,
    role: UserRole,
    academic_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_email = email.lower()
    now = datetime.now(timezone.utc)
    if role == UserRole.USER and academic_profile is None:
        raise InvalidStudentAcademicProfileError
    account_status = AccountStatus.ACTIVE if role == UserRole.ADMIN else AccountStatus.PENDING
    document = {
        "full_name": full_name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(password),
        "role": role.value,
        "is_active": account_status == AccountStatus.ACTIVE,
        "account_status": account_status.value,
        "status_changed_at": None,
        "status_changed_by": None,
        "email_verified": False,
        "created_at": now,
        "updated_at": now,
    }
    if academic_profile is not None:
        document["academic_profile"] = serialize_academic_profile(AcademicProfileInput.model_validate(academic_profile))
    try:
        return public_user(users.create(document))
    except DuplicateKeyError as error:
        raise ConflictError from error


def register_user(
    users: UserRepository,
    email: str,
    password: str,
    full_name: str = "",
    academic_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_email = email.lower()
    role = UserRole.ADMIN if normalized_email in security_config["ADMIN_EMAILS"] else UserRole.USER
    return _create_account(users, email, password, full_name, role=role, academic_profile=academic_profile)


def create_trainer_user(users: UserRepository, email: str, password: str, full_name: str = "") -> dict[str, Any]:
    return _create_account(users, email, password, full_name, role=UserRole.TRAINER)


def authenticate(users: UserRepository, refresh_tokens: RefreshTokenRepository, email: str, password: str) -> dict[str, Any]:
    user = users.find_by_email(email.lower())
    if not user or not verify_password(password, user["password_hash"]):
        raise AuthenticationError
    if not user.get("email_verified", True):
        raise EmailNotVerifiedError
    ensure_active_account(user)
    access, expires_in = create_access_token(str(user["_id"]), user["role"])
    refresh, refresh_expires = create_refresh_token(str(user["_id"]), user["role"])
    refresh_tokens.create({"token_hash": hash_token(refresh), "user_id": user["_id"], "expires_at": refresh_expires, "created_at": datetime.now(timezone.utc), "revoked_at": None})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "expires_in": expires_in, "user": public_user(user)}


def refresh_session(users: UserRepository, refresh_tokens: RefreshTokenRepository, token: str) -> dict[str, Any]:
    from app.core.security import decode_refresh_token

    try:
        payload = decode_refresh_token(token)
        stored = refresh_tokens.find_active(hash_token(token))
        user = users.find_by_id(stored["user_id"]) if stored else None
    except Exception as error:
        raise AuthenticationError from error
    if not stored or not user:
        raise AuthenticationError
    ensure_active_account(user)
    refresh_tokens.revoke(hash_token(token))
    access, expires_in = create_access_token(str(user["_id"]), user["role"])
    new_refresh, refresh_expires = create_refresh_token(str(user["_id"]), user["role"])
    refresh_tokens.create({"token_hash": hash_token(new_refresh), "user_id": user["_id"], "expires_at": refresh_expires, "created_at": datetime.now(timezone.utc), "revoked_at": None})
    return {"access_token": access, "refresh_token": new_refresh, "token_type": "bearer", "expires_in": expires_in, "user": public_user(user)}


def update_profile(users: UserRepository, user: dict[str, Any], *, full_name: str | None = None, email: str | None = None, current_password: str | None = None, new_password: str | None = None) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    if full_name is not None:
        changes["full_name"] = full_name.strip()
    if email is not None:
        if not current_password or not verify_password(current_password, user["password_hash"]):
            raise AuthenticationError
        changes["email"] = email.lower()
    if new_password is not None:
        if not current_password or not verify_password(current_password, user["password_hash"]):
            raise AuthenticationError
        changes["password_hash"] = hash_password(new_password)
    updated = users.update(user["_id"], changes)
    if not updated:
        raise NotFoundError
    return public_user(updated)
