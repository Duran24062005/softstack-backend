from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


class ContentRevisionRepository:
    def __init__(self, database: Database):
        self.collection = database.content_revisions

    def find_by_id(self, revision_id: ObjectId) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": revision_id})

    def find_pending(self, target_type: str, target_id: ObjectId) -> dict[str, Any] | None:
        return self.collection.find_one({"target_type": target_type, "target_id": target_id, "status": "pending"})

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        stored = {"created_at": now, "updated_at": now, "status": "pending", **document}
        result = self.collection.insert_one(stored)
        stored["_id"] = result.inserted_id
        return stored

    def update(self, revision_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        self.collection.update_one(
            {"_id": revision_id, "status": "pending"},
            {"$set": {**changes, "updated_at": datetime.now(timezone.utc)}},
        )
        return self.find_by_id(revision_id)

    def mark(self, revision_id: ObjectId, status: str) -> dict[str, Any] | None:
        return self.update(revision_id, {"status": status})

    def delete(self, revision_id: ObjectId) -> dict[str, Any] | None:
        document = self.find_by_id(revision_id)
        if document and document.get("status") == "pending":
            self.collection.delete_one({"_id": revision_id, "status": "pending"})
        return document
