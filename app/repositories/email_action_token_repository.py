from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


class EmailActionTokenRepository:
    def __init__(self, database: Database):
        self.collection = database.email_action_tokens

    def invalidate_active(self, user_id: Any, purpose: str) -> None:
        self.collection.update_many(
            {"user_id": user_id, "purpose": purpose, "consumed_at": None},
            {"$set": {"consumed_at": datetime.now(timezone.utc)}},
        )

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def find_active_by_hash(self, token_hash: str, purpose: str) -> dict[str, Any] | None:
        return self.collection.find_one(
            {
                "token_hash": token_hash,
                "purpose": purpose,
                "consumed_at": None,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            }
        )

    def find_active_for_user(self, user_id: Any, purpose: str) -> dict[str, Any] | None:
        return self.collection.find_one(
            {
                "user_id": user_id,
                "purpose": purpose,
                "consumed_at": None,
                "expires_at": {"$gt": datetime.now(timezone.utc)},
            },
            sort=[("created_at", -1)],
        )

    def increment_attempts(self, token_id: Any) -> None:
        self.collection.update_one({"_id": token_id}, {"$inc": {"attempts": 1}})

    def consume(self, token_id: Any) -> None:
        self.collection.update_one(
            {"_id": token_id, "consumed_at": None},
            {"$set": {"consumed_at": datetime.now(timezone.utc)}},
        )
