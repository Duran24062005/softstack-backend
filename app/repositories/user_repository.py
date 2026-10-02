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
