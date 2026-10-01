from datetime import datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class User(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId | None = Field(default=None, alias="_id")
    full_name: str = ""
    email: EmailStr
    password_hash: str
    role: UserRole = UserRole.USER
    is_active: bool = True
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
    return {
        "id": str(document["_id"]),
        "full_name": document.get("full_name") or email.split("@", 1)[0],
        "email": email,
        "role": document["role"],
        "is_active": document["is_active"],
        "created_at": document["created_at"],
    }
