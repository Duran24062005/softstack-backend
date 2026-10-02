from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from app.models.auth import UserRole


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    new_password: str = Field(min_length=8, max_length=128)


class EmailRequest(BaseModel):
    email: EmailStr


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=80)
    email: EmailStr | None = None
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_changes(self):
        if self.full_name is None and self.email is None and self.new_password is None:
            raise ValueError("At least one profile field is required")
        if (self.email is not None or self.new_password is not None) and not self.current_password:
            raise ValueError("Current password is required for credential changes")
        return self


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    email_verified: bool
    has_profile_photo: bool = False
    created_at: datetime


class AuthResponse(BaseModel):
    expires_in: int = 0
    user: UserResponse
    verification_required: bool = False
    message: str | None = None
