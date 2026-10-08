from typing import Any

from app.core.exception import (
    AccountPendingApprovalError,
    AccountRejectedError,
    AuthorizationError,
    InactiveUserError,
    InvalidAccountStatusTransitionError,
    NotFoundError,
)
from app.models.auth import AccountStatus, admin_user, effective_account_status
from app.repositories.user_repository import UserRepository


ALLOWED_STATUS_TRANSITIONS: dict[AccountStatus, set[AccountStatus]] = {
    AccountStatus.PENDING: {AccountStatus.ACTIVE, AccountStatus.REJECTED},
    AccountStatus.REJECTED: {AccountStatus.PENDING},
    AccountStatus.ACTIVE: {AccountStatus.INACTIVE},
    AccountStatus.INACTIVE: {AccountStatus.ACTIVE},
}


def ensure_active_account(user: dict[str, Any]) -> dict[str, Any]:
    status = effective_account_status(user)
    if status == AccountStatus.PENDING:
        raise AccountPendingApprovalError
    if status == AccountStatus.REJECTED:
        raise AccountRejectedError
    if status != AccountStatus.ACTIVE:
        raise InactiveUserError
    return user


def update_account_status(
    users: UserRepository,
    user_id: Any,
    requested_status: AccountStatus,
    admin_actor: dict[str, Any],
) -> dict[str, Any]:
    target = users.find_by_id(user_id)
    if not target:
        raise NotFoundError
    if target["_id"] == admin_actor["_id"] or target.get("role") == "admin":
        raise AuthorizationError

    current_status = effective_account_status(target)
    if requested_status not in ALLOWED_STATUS_TRANSITIONS[current_status]:
        raise InvalidAccountStatusTransitionError

    updated = users.update_account_status(
        target["_id"],
        requested_status,
        admin_actor["_id"],
    )
    if not updated:
        raise NotFoundError
    return admin_user(updated)
