from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.content import ContentStatus
from app.schemas.content_media import MediaReference


class TiptapDocumentRequest(BaseModel):
    type: Literal["doc"] = "doc"
    content: list[dict[str, Any]] = Field(default_factory=list)


class ModuleCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=500)
    order: int = Field(default=0, ge=0)
    status: ContentStatus = ContentStatus.DRAFT
    cover_media: MediaReference | None = None


class ModuleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    order: int | None = Field(default=None, ge=0)
    status: ContentStatus | None = None
    cover_media: MediaReference | None = None


class ModuleResponse(BaseModel):
    id: str
    title: str
    slug: str
    description: str
    order: int
    status: ContentStatus
    cover_media: MediaReference | None = None
    created_at: datetime
    updated_at: datetime


class LessonCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    content: TiptapDocumentRequest = Field(default_factory=TiptapDocumentRequest)
    order: int = Field(default=0, ge=0)
    status: ContentStatus = ContentStatus.DRAFT
    estimated_minutes: int = Field(default=10, ge=1, le=240)


class LessonUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=600)
    content: TiptapDocumentRequest | None = None
    order: int | None = Field(default=None, ge=0)
    status: ContentStatus | None = None
    estimated_minutes: int | None = Field(default=None, ge=1, le=240)


class LessonResponse(BaseModel):
    id: str
    module_id: str
    title: str
    slug: str
    description: str
    content: TiptapDocumentRequest
    order: int
    status: ContentStatus
    estimated_minutes: int
    created_at: datetime
    updated_at: datetime


class ProgressSummaryResponse(BaseModel):
    completed_lesson_ids: list[str]
    completed_count: int
    total_lessons: int
    percentage: float
    completed_module_ids: list[str] = []
    completed_module_count: int = 0
    total_modules: int = 0
    module_percentage: float = 0
