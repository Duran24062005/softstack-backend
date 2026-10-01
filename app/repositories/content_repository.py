from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.database import Database


class ModuleRepository:
    def __init__(self, database: Database):
        self.collection = database.modules

    def list(self, status: str | None = None) -> list[dict[str, Any]]:
        query = {"status": status} if status else {}
        return list(self.collection.find(query).sort("order", 1))

    def find_by_id(self, module_id: ObjectId) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": module_id})

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, module_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        changes = {**changes, "updated_at": datetime.now(timezone.utc)}
        self.collection.update_one({"_id": module_id}, {"$set": changes})
        return self.find_by_id(module_id)


class LessonRepository:
    def __init__(self, database: Database):
        self.collection = database.lessons

    def list(self, module_id: ObjectId | None = None, status: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if module_id:
            query["module_id"] = module_id
        if status:
            query["status"] = status
        return list(self.collection.find(query).sort("order", 1))

    def find_by_id(self, lesson_id: ObjectId) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": lesson_id})

    def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, lesson_id: ObjectId, changes: dict[str, Any]) -> dict[str, Any] | None:
        changes = {**changes, "updated_at": datetime.now(timezone.utc)}
        self.collection.update_one({"_id": lesson_id}, {"$set": changes})
        return self.find_by_id(lesson_id)


class ProgressRepository:
    def __init__(self, database: Database):
        self.collection = database.progress

    def completed_for_user(self, user_id: ObjectId) -> list[dict[str, Any]]:
        return list(self.collection.find({"user_id": user_id}).sort("completed_at", 1))

    def complete(self, user_id: ObjectId, lesson_id: ObjectId, module_id: ObjectId) -> None:
        self.collection.update_one(
            {"user_id": user_id, "lesson_id": lesson_id},
            {"$setOnInsert": {"user_id": user_id, "lesson_id": lesson_id, "module_id": module_id, "completed_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
