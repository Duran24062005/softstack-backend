from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database


class RefreshTokenRepository:
    def __init__(self, database: Database):
        self.collection = database.refresh_tokens

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def find_active(self, token_hash: str) -> dict[str, Any] | None:
        return self.collection.find_one({"token_hash": token_hash, "revoked_at": None, "expires_at": {"$gt": datetime.now(timezone.utc)}})

    def revoke(self, token_hash: str) -> None:
        self.collection.update_one({"token_hash": token_hash}, {"$set": {"revoked_at": datetime.now(timezone.utc)}})

    def revoke_for_user(self, user_id: Any) -> None:
        self.collection.update_many(
            {"user_id": user_id, "revoked_at": None},
            {"$set": {"revoked_at": datetime.now(timezone.utc)}},
        )
