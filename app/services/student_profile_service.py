from typing import Any

from app.core.exception import AuthorizationError, NotFoundError
from app.models.auth import UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.student_profile import AcademicProfileInput


def serialize_academic_profile(payload: AcademicProfileInput) -> dict[str, Any]:
    return payload.model_dump(mode="json")


def normalize_academic_profile(profile: dict[str, Any] | None) -> dict[str, Any] | None:
    """Read the previous memberships shape without requiring a data migration."""
    if not profile:
        return None
    if profile.get("group_name") and profile.get("campus_name"):
        return profile

    memberships = profile.get("memberships") or []
    selected = next((item for item in memberships if item.get("is_current")), memberships[0] if memberships else None)
    if not selected or not selected.get("group_name") or not selected.get("campus_name"):
        return None
    return {
        "start_year": profile.get("start_year"),
        "group_name": selected["group_name"],
        "campus_name": selected["campus_name"],
        "linkedin_url": profile.get("linkedin_url"),
        "github_url": profile.get("github_url"),
    }


def get_academic_profile(user: dict[str, Any]) -> dict[str, Any] | None:
    profile = normalize_academic_profile(user.get("academic_profile"))
    if not profile:
        return None
    return serialize_academic_profile(AcademicProfileInput.model_validate(profile))


def save_academic_profile(
    users: UserRepository,
    user: dict[str, Any],
    payload: AcademicProfileInput,
) -> dict[str, Any]:
    if user.get("role") != UserRole.USER.value:
        raise AuthorizationError
    updated = users.update(user["_id"], {"academic_profile": serialize_academic_profile(payload)})
    if not updated:
        raise NotFoundError
    return updated["academic_profile"]


def save_admin_academic_profile(
    users: UserRepository,
    student: dict[str, Any],
    payload: AcademicProfileInput,
) -> dict[str, Any]:
    if student.get("role") != UserRole.USER.value:
        raise AuthorizationError
    updated = users.update(student["_id"], {"academic_profile": serialize_academic_profile(payload)})
    if not updated:
        raise NotFoundError
    return updated["academic_profile"]
