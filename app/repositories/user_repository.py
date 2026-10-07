from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


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
