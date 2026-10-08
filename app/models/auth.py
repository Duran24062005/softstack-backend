from datetime import datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    USER = "user"
    TRAINER = "trainer"
    ADMIN = "admin"


class AccountStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REJECTED = "rejected"
    INACTIVE = "inactive"


class User(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId | None = Field(default=None, alias="_id")
    full_name: str = ""
    email: EmailStr
    password_hash: str
    profile_photo: dict[str, Any] | None = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    account_status: AccountStatus = AccountStatus.ACTIVE
    status_changed_at: datetime | None = None
    status_changed_by: ObjectId | None = None
    email_verified: bool = True
    created_at: datetime
    updated_at: datetime


class RefreshToken(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId | None = Field(default=None, alias="_id")
    token_hash: str
    user_id: ObjectId
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None


def public_user(document: dict[str, Any]) -> dict[str, Any]:
    email = document["email"]
    account_status = effective_account_status(document)
    return {
        "id": str(document["_id"]),
        "full_name": document.get("full_name") or email.split("@", 1)[0],
        "email": email,
        "role": document["role"],
        "is_active": account_status == AccountStatus.ACTIVE,
        "account_status": account_status,
        "email_verified": document.get("email_verified", True),
        "has_profile_photo": bool(document.get("profile_photo")),
        "created_at": document["created_at"],
    }


def admin_user(document: dict[str, Any]) -> dict[str, Any]:
    payload = public_user(document)
    payload.update(
        {
            "status_changed_at": document.get("status_changed_at"),
            "status_changed_by": str(document["status_changed_by"]) if document.get("status_changed_by") else None,
        }
    )
    return payload


def effective_account_status(document: dict[str, Any]) -> AccountStatus:
    raw_status = document.get("account_status")
    if raw_status:
        try:
            return AccountStatus(raw_status)
        except ValueError:
            pass
    return AccountStatus.ACTIVE if document.get("is_active", True) else AccountStatus.INACTIVE
