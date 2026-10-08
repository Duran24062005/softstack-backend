from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

from app.models.auth import AccountStatus


class UserRepository:
    def __init__(self, database: Database):
        self.collection = database.users

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email.lower()})

    def find_by_id(self, user_id: Any) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": user_id})

    def list_by_ids(self, user_ids: list[Any]) -> list[dict[str, Any]]:
        if not user_ids:
            return []
        return list(self.collection.find({"_id": {"$in": user_ids}}).sort("full_name", 1))

    def list_by_role(self, role: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"role": role}).sort("full_name", 1))

    def list_users(self, *, role: str | None = None, account_status: AccountStatus | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if role:
            query["role"] = role
        if account_status:
            if account_status == AccountStatus.ACTIVE:
                query["$or"] = [
                    {"account_status": AccountStatus.ACTIVE.value},
                    {"account_status": {"$exists": False}, "is_active": True},
                ]
            elif account_status == AccountStatus.INACTIVE:
                query["$or"] = [
                    {"account_status": AccountStatus.INACTIVE.value},
                    {"account_status": {"$exists": False}, "is_active": False},
                ]
            else:
                query["account_status"] = account_status.value
        return list(self.collection.find(query).sort("full_name", 1))

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def touch(self, user_id: Any) -> None:
        self.collection.update_one({"_id": user_id}, {"$set": {"updated_at": datetime.now(timezone.utc)}})

    def update(self, user_id: Any, changes: dict[str, Any]) -> dict[str, Any] | None:
        changes = {**changes, "updated_at": datetime.now(timezone.utc)}
        self.collection.update_one({"_id": user_id}, {"$set": changes})
        return self.find_by_id(user_id)

    def mark_email_verified(self, user_id: Any) -> dict[str, Any] | None:
        return self.update(user_id, {"email_verified": True})

    def update_account_status(self, user_id: Any, account_status: AccountStatus, admin_id: Any) -> dict[str, Any] | None:
        return self.update(
            user_id,
            {
                "account_status": account_status.value,
                "is_active": account_status == AccountStatus.ACTIVE,
                "status_changed_at": datetime.now(timezone.utc),
                "status_changed_by": admin_id,
            },
        )
