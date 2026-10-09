from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.content import TiptapDocumentRequest
from app.schemas.instructional import ContentFormat, GeneratedContentBlock, InstructionalPlan, OrderingStrategy
SuggestionMode = Literal["create", "organize"]
PlanSection = Literal["fields", "objectives", "concept_map", "formats", "session_plan", "lesson_sequence"]
LessonApplySection = Literal["fields", "objectives", "concept_map", "formats", "session_plan", "content"]


class LessonSuggestionContext(BaseModel):
    id: str | None = None
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    order: int = Field(default=0, ge=0)
    estimated_minutes: int = Field(default=10, ge=1, le=240)
    instructional_plan: InstructionalPlan | None = None


class ModuleSuggestionRequest(BaseModel):
    mode: SuggestionMode = "create"
    module_id: str | None = None
    topic: str = Field(default="", max_length=240)
    title: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)
    audience: str = Field(default="Estudiantes de formación profesional", max_length=240)
    level: str = Field(default="intermedio", max_length=80)
    lesson_count: int = Field(default=5, ge=1, le=12)
    lessons: list[LessonSuggestionContext] = Field(default_factory=list, max_length=50)
    base_updated_at: datetime | None = None


class LessonSuggestionRequest(BaseModel):
    mode: SuggestionMode = "create"
    lesson_id: str | None = None
    topic: str = Field(default="", max_length=240)
    title: str = Field(default="", max_length=160)
    description: str = Field(default="", max_length=600)
    objective: str = Field(default="", max_length=400)
    module_title: str = Field(default="", max_length=160)
    module_description: str = Field(default="", max_length=500)
    audience: str = Field(default="Estudiantes de formación profesional", max_length=240)
    level: str = Field(default="intermedio", max_length=80)
    estimated_minutes: int = Field(default=20, ge=1, le=240)
    content: TiptapDocumentRequest = Field(default_factory=TiptapDocumentRequest)
    instructional_plan: InstructionalPlan | None = None
    base_updated_at: datetime | None = None


class GeneratedModuleSuggestion(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=500)
    instructional_plan: InstructionalPlan


class GeneratedLessonSuggestion(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    estimated_minutes: int = Field(default=20, ge=1, le=240)
    instructional_plan: InstructionalPlan
    blocks: list[GeneratedContentBlock] = Field(min_length=1, max_length=80)


class ContentSuggestionResponse(BaseModel):
    target_type: Literal["module", "lesson"]
    mode: SuggestionMode
    target_id: str | None = None
    base_updated_at: datetime | None = None
    provider: str
    model: str | None = None
    title: str
    description: str
    estimated_minutes: int | None = None
    instructional_plan: InstructionalPlan
    content: TiptapDocumentRequest | None = None


class LessonOrderChange(BaseModel):
    lesson_id: str
    order: int = Field(ge=0)


class ModuleApplyRequest(BaseModel):
    base_updated_at: datetime
    plan_sections: list[PlanSection] = Field(min_length=1)
    title: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=500)
    instructional_plan: InstructionalPlan
    lesson_orders: list[LessonOrderChange] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_fields(self) -> ModuleApplyRequest:
        if "fields" in self.plan_sections and len(self.title.strip()) < 3:
            raise ValueError("Title is required when applying module fields")
        return self

class LessonApplyRequest(BaseModel):
    base_updated_at: datetime
    sections: list[LessonApplySection] = Field(min_length=1)
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    estimated_minutes: int = Field(default=20, ge=1, le=240)
    instructional_plan: InstructionalPlan
    content: TiptapDocumentRequest | None = None


class ContentRevisionResponse(BaseModel):
    id: str
    target_type: Literal["module", "lesson"]
    target_id: str
    status: Literal["pending", "published", "discarded"]
    source: Literal["ai_content_suggestion"]
    base_updated_at: datetime
    created_at: datetime
    updated_at: datetime


class ContentApplyResponse(BaseModel):
    outcome: Literal["updated", "revision_created"]
    revision: ContentRevisionResponse | None = None
    module: dict | None = None
    lesson: dict | None = None


__all__ = [
    "ContentApplyResponse",
    "ContentRevisionResponse",
    "ContentSuggestionResponse",
    "GeneratedLessonSuggestion",
    "GeneratedModuleSuggestion",
    "LessonApplyRequest",
    "LessonApplySection",
    "LessonSuggestionRequest",
    "ModuleApplyRequest",
    "ModuleSuggestionRequest",
]
