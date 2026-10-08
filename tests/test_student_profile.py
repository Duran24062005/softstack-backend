from datetime import date, datetime, timezone
from unittest.mock import Mock

import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.core.exception import AuthorizationError, InvalidStudentAcademicProfileError
from app.models.auth import UserRole
from app.repositories.user_repository import UserRepository
from app.routes.auth_routes import get_my_academic_profile, update_my_academic_profile
from app.routes.user_routes import get_student_academic_profile, update_student_academic_profile
from app.schemas.student_profile import AcademicProfileInput
from app.services.auth_service import create_trainer_user, register_user


def profile(**changes):
    value = {
        "start_year": 2024,
        "group_name": "Grupo A",
        "campus_name": "Bucaramanga",
        "linkedin_url": None,
        "github_url": "https://github.com/student",
    }
    value.update(changes)
    return value


def student_document(*, role="user", academic_profile=None):
    return {
        "_id": ObjectId(),
        "email": "student@example.com",
        "full_name": "Student",
        "role": role,
        "academic_profile": academic_profile,
        "is_active": True,
        "email_verified": True,
        "created_at": datetime.now(timezone.utc),
    }


def test_academic_profile_validates_domains_and_year():
    parsed = AcademicProfileInput.model_validate(profile())
    assert str(parsed.github_url) == "https://github.com/student"

    with pytest.raises(ValidationError):
        AcademicProfileInput.model_validate(profile(start_year=date.today().year + 1))
    with pytest.raises(ValidationError):
        AcademicProfileInput.model_validate(profile(linkedin_url="https://example.com/person"))
    with pytest.raises(ValidationError):
        AcademicProfileInput.model_validate({**profile(), "memberships": [{"group_name": "Old", "campus_name": "Past"}]})


def test_student_registration_requires_academic_profile_but_trainers_do_not():
    users = Mock(spec=UserRepository)
    users.create.side_effect = lambda document: {**document, "_id": ObjectId()}

    with pytest.raises(InvalidStudentAcademicProfileError):
        register_user(users, "student@example.com", "strong-password")

    trainer = create_trainer_user(users, "trainer@example.com", "strong-password", "Trainer")
    assert trainer["role"] == UserRole.TRAINER.value
    assert "academic_profile" not in users.create.call_args.args[0]


def test_register_persists_academic_profile_without_exposing_it_in_public_user():
    users = Mock(spec=UserRepository)
    users.create.side_effect = lambda document: {**document, "_id": ObjectId()}

    result = register_user(users, "student@example.com", "strong-password", academic_profile=profile())

    assert result["role"] == UserRole.USER.value
    assert "academic_profile" not in result
    assert users.create.call_args.args[0]["academic_profile"] == profile()


def test_student_can_read_and_update_own_academic_profile():
    student = student_document(academic_profile=profile())
    users = Mock(spec=UserRepository)
    def update(user_id, changes):
        student.update(changes)
        student["_id"] = user_id
        return student

    users.update.side_effect = update

    assert get_my_academic_profile(student)["start_year"] == 2024
    updated = update_my_academic_profile(AcademicProfileInput.model_validate(profile(start_year=2025)), user=student, users=users)

    assert updated["start_year"] == 2025
    assert users.update.call_args.args[1]["academic_profile"]["start_year"] == 2025


def test_admin_can_manage_student_profile_but_non_students_are_rejected():
    student = student_document(academic_profile=None)
    admin = student_document(role="admin")
    users = Mock(spec=UserRepository)
    users.find_by_id.return_value = student

    def update(user_id, changes):
        student.update(changes)
        student["_id"] = user_id
        return student

    users.update.side_effect = update

    saved = update_student_academic_profile(str(student["_id"]), AcademicProfileInput.model_validate(profile()), _=admin, users=users)
    assert saved["group_name"] == "Grupo A"
    assert get_student_academic_profile(str(student["_id"]), _=admin, users=users)["start_year"] == 2024

    users.find_by_id.return_value = student_document(role="trainer")
    with pytest.raises(AuthorizationError):
        get_student_academic_profile(str(student["_id"]), _=admin, users=users)

    with pytest.raises(AuthorizationError):
        update_my_academic_profile(AcademicProfileInput.model_validate(profile()), user=student_document(role="trainer"), users=users)


def test_existing_membership_profile_is_read_as_final_group_and_campus():
    legacy = {
        "start_year": 2024,
        "linkedin_url": None,
        "github_url": None,
        "memberships": [
            {"id": "old", "group_name": "Grupo anterior", "campus_name": "Bogotá", "is_current": False},
            {"id": "current", "group_name": "Grupo final", "campus_name": "Bucaramanga", "is_current": True},
        ],
    }
    assert get_my_academic_profile(student_document(academic_profile=legacy)) == {
        "start_year": 2024,
        "group_name": "Grupo final",
        "campus_name": "Bucaramanga",
        "linkedin_url": None,
        "github_url": None,
    }
