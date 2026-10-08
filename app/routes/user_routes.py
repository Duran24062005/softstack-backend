from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.core.exception import NotFoundError
from app.models.auth import AccountStatus, UserRole, admin_user
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import get_user_repository
from app.middlewares.role_middleware import require_roles
from app.schemas.auth import AdminUserResponse, AccountStatusUpdateRequest
from app.services.account_status_service import update_account_status


router = APIRouter(tags=["users"])
admin = require_roles("admin")


@router.get("/admin/users", response_model=list[AdminUserResponse])
def list_users(
    _: dict = Depends(admin),
    role: UserRole | None = Query(default=None),
    account_status: AccountStatus | None = Query(default=None),
    users: UserRepository = Depends(get_user_repository),
):
    return [admin_user(user) for user in users.list_users(role=role.value if role else None, account_status=account_status)]


@router.patch("/admin/users/{user_id}/status", response_model=AdminUserResponse)
def change_user_status(
    user_id: str,
    payload: AccountStatusUpdateRequest,
    admin_user_context: dict = Depends(admin),
    users: UserRepository = Depends(get_user_repository),
):
    if not ObjectId.is_valid(user_id):
        raise NotFoundError
    return update_account_status(users, ObjectId(user_id), payload.account_status, admin_user_context)
