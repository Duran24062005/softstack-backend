from __future__ import annotations

from typing import Any

from bson import ObjectId
from pymongo.database import Database


class ContentMediaRepository:
    """Reads media references from content documents for safe cleanup."""

    def __init__(self, database: Database):
        self.modules = database.modules
        self.lessons = database.lessons

    def is_referenced(
        self,
        pathname: str,
        *,
        excluded_module_id: ObjectId | None = None,
        excluded_lesson_id: ObjectId | None = None,
    ) -> bool:
        module_query: dict[str, Any] = {"media_assets.pathname": pathname}
        lesson_query: dict[str, Any] = {"media_assets.pathname": pathname}
        if excluded_module_id is not None:
            module_query["_id"] = {"$ne": excluded_module_id}
        if excluded_lesson_id is not None:
            lesson_query["_id"] = {"$ne": excluded_lesson_id}
        return bool(self.modules.find_one(module_query, {"_id": 1}) or self.lessons.find_one(lesson_query, {"_id": 1}))

    def referenced_pathnames(self) -> set[str]:
        paths: set[str] = set()
        for collection in (self.modules, self.lessons):
            for document in collection.find({}, {"media_assets.pathname": 1}):
                paths.update(
                    asset["pathname"]
                    for asset in document.get("media_assets", [])
                    if asset.get("pathname")
                )
        return paths
