from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from bson import ObjectId

from app.config.config import security_config
from app.core.exception import (
    AccountPendingApprovalError,
    AccountRejectedError,
    AuthorizationError,
    InactiveUserError,
    InvalidAccountStatusTransitionError,
)
from app.models.auth import AccountStatus, UserRole, effective_account_status
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.routes.user_routes import change_user_status, list_users
from app.schemas.auth import AccountStatusUpdateRequest
from app.services.account_status_service import ensure_active_account, update_account_status
from app.services.auth_service import authenticate, register_user
from app.core.security import hash_password


VALID_ACADEMIC_PROFILE = {
    "start_year": 2024,
    "group_name": "Grupo A",
    "campus_name": "Bucaramanga",
    "linkedin_url": None,
    "github_url": None,
}


def make_user(*, role: str = "user", status: str = "active", verified: bool = True) -> dict:
    return {
        "_id": ObjectId(),
        "full_name": role.title(),
        "email": f"{role}-{ObjectId()}@example.com",
        "password_hash": hash_password("strong-password"),
        "role": role,
        "account_status": status,
        "is_active": status == "active",
        "email_verified": verified,
        "created_at": datetime.now(timezone.utc),
    }


def test_registration_starts_pending_but_allowlisted_admin_is_active(monkeypatch):
    users = Mock(spec=UserRepository)
    users.create.side_effect = lambda document: {**document, "_id": ObjectId()}
    monkeypatch.setitem(security_config, "ADMIN_EMAILS", ["admin@example.com"])

    student = register_user(users, "student@example.com", "strong-password", academic_profile=VALID_ACADEMIC_PROFILE)
    student_document = users.create.call_args.args[0]
    assert student["account_status"] == "pending"
    assert student["is_active"] is False
    assert student_document["account_status"] == "pending"

    admin = register_user(users, "admin@example.com", "strong-password")
    admin_document = users.create.call_args.args[0]
    assert admin["role"] == UserRole.ADMIN.value
    assert admin["account_status"] == "active"
    assert admin_document["is_active"] is True


@pytest.mark.parametrize(
    ("status", "error"),
    [
        ("pending", AccountPendingApprovalError),
        ("rejected", AccountRejectedError),
        ("inactive", InactiveUserError),
    ],
)
def test_login_rejects_every_non_active_status(status, error):
    users = Mock(spec=UserRepository)
    refresh_tokens = Mock(spec=RefreshTokenRepository)
    user = make_user(status=status)
    users.find_by_email.return_value = user

    with pytest.raises(error):
        authenticate(users, refresh_tokens, user["email"], "strong-password")

    refresh_tokens.create.assert_not_called()


def test_email_verification_does_not_approve_account():
    user = make_user(status="pending", verified=False)
    assert effective_account_status(user) == AccountStatus.PENDING

    with pytest.raises(AccountPendingApprovalError):
        ensure_active_account({**user, "email_verified": True})


def test_status_transitions_update_access_flag_and_actor():
    users = Mock(spec=UserRepository)
    target = make_user(status="pending")
    actor = make_user(role="admin")
    users.find_by_id.return_value = target
    users.update_account_status.side_effect = lambda user_id, status, admin_id: {
        **target,
        "_id": user_id,
        "account_status": status.value,
        "is_active": status == AccountStatus.ACTIVE,
        "status_changed_by": admin_id,
        "status_changed_at": datetime.now(timezone.utc),
    }

    updated = update_account_status(users, target["_id"], AccountStatus.ACTIVE, actor)

    assert updated["account_status"] == AccountStatus.ACTIVE
    assert updated["is_active"] is True
    users.update_account_status.assert_called_once_with(target["_id"], AccountStatus.ACTIVE, actor["_id"])


def test_status_transition_rejects_invalid_changes_and_protects_admins():
    users = Mock(spec=UserRepository)
    actor = make_user(role="admin")
    target = make_user(status="pending")
    users.find_by_id.return_value = target

    with pytest.raises(InvalidAccountStatusTransitionError):
        update_account_status(users, target["_id"], AccountStatus.INACTIVE, actor)

    users.find_by_id.return_value = actor
    with pytest.raises(AuthorizationError):
        update_account_status(users, actor["_id"], AccountStatus.INACTIVE, actor)


def test_admin_user_routes_list_all_roles_and_delegate_status_changes():
    admin = make_user(role="admin")
    users = Mock(spec=UserRepository)
    users.list_users.return_value = [make_user(role="admin"), make_user(role="trainer"), make_user(role="user")]
    listed = list_users(admin, role=None, account_status=None, users=users)

    assert {entry["role"] for entry in listed} == {"admin", "trainer", "user"}
    users.list_users.assert_called_once_with(role=None, account_status=None)

    target = make_user(status="inactive")
    users.find_by_id.return_value = target
    users.update_account_status.return_value = {**target, "account_status": "active", "is_active": True}
    changed = change_user_status(
        str(target["_id"]),
        AccountStatusUpdateRequest(account_status=AccountStatus.ACTIVE),
        admin_user_context=admin,
        users=users,
    )
    assert changed["account_status"] == AccountStatus.ACTIVE
