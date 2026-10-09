from datetime import datetime
from enum import Enum
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.content_media import MediaReference
from app.schemas.instructional import InstructionalPlan


class ContentStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TiptapDocument(BaseModel):
    type: str = "doc"
    content: list[dict[str, Any]] = Field(default_factory=list)


class LearningModule(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId | None = Field(default=None, alias="_id")
    title: str
    slug: str
    description: str
    order: int = 0
    status: ContentStatus = ContentStatus.DRAFT
    cover_media: MediaReference | None = None
    instructional_plan: InstructionalPlan | None = None
    media_assets: list[MediaReference] = Field(default_factory=list)
    created_by: ObjectId
    created_at: datetime
    updated_at: datetime


class Lesson(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: ObjectId | None = Field(default=None, alias="_id")
    module_id: ObjectId
    title: str
    slug: str
    description: str
    content: TiptapDocument = Field(default_factory=TiptapDocument)
    instructional_plan: InstructionalPlan | None = None
    media_assets: list[MediaReference] = Field(default_factory=list)
    order: int = 0
    status: ContentStatus = ContentStatus.DRAFT
    estimated_minutes: int = 10
    created_by: ObjectId
    updated_by: ObjectId
    created_at: datetime
    updated_at: datetime


def public_module(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document["title"],
        "slug": document["slug"],
        "description": document.get("description", ""),
        "order": document.get("order", 0),
        "status": document.get("status", ContentStatus.DRAFT.value),
        "cover_media": document.get("cover_media"),
        "instructional_plan": document.get("instructional_plan"),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


def public_lesson(document: dict[str, Any], include_content: bool = True) -> dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "module_id": str(document["module_id"]),
        "title": document["title"],
        "slug": document["slug"],
        "description": document.get("description", ""),
        "order": document.get("order", 0),
        "status": document.get("status", ContentStatus.DRAFT.value),
        "estimated_minutes": document.get("estimated_minutes", 10),
        "instructional_plan": document.get("instructional_plan"),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }
    if include_content:
        payload["content"] = document.get("content", {"type": "doc", "content": []})
    return payload
