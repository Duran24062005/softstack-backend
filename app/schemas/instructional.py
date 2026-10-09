from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


ContentFormat = Literal["text", "video", "activity", "interactive", "gamification"]
OrderingStrategy = Literal[
    "simple_to_complex",
    "chronological",
    "categorical",
    "cause_effect",
    "hierarchy",
    "alphabetical",
]


class ConceptMapNode(BaseModel):
    label: str = Field(min_length=1, max_length=160)
    children: list[ConceptMapNode] = Field(default_factory=list, max_length=8)


class SessionPlanItem(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    minutes: int = Field(ge=1, le=240)
    activity: str = Field(min_length=2, max_length=500)
    format: ContentFormat


class LessonBlueprint(BaseModel):
    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9-]+$")
    source_id: str | None = Field(default=None, max_length=64)
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=600)
    objective: str = Field(min_length=10, max_length=400)
    estimated_minutes: int = Field(default=10, ge=1, le=240)
    recommended_formats: list[ContentFormat] = Field(min_length=1, max_length=5)


class InstructionalPlan(BaseModel):
    central_topic: str = Field(min_length=3, max_length=240)
    learning_objectives: list[str] = Field(min_length=1, max_length=8)
    concept_map: ConceptMapNode | None = None
    ordering_strategy: OrderingStrategy = "simple_to_complex"
    ordering_rationale: str = Field(min_length=10, max_length=600)
    recommended_formats: list[ContentFormat] = Field(min_length=1, max_length=5)
    session_plan: list[SessionPlanItem] = Field(min_length=1, max_length=12)
    lesson_sequence: list[LessonBlueprint] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def validate_lesson_keys(self) -> InstructionalPlan:
        keys = [lesson.key for lesson in self.lesson_sequence]
        if len(keys) != len(set(keys)):
            raise ValueError("Lesson blueprint keys must be unique")
        return self


SafeBlockType = Literal[
    "heading",
    "paragraph",
    "bullet_list",
    "ordered_list",
    "blockquote",
    "code_block",
    "horizontal_rule",
]


class GeneratedContentBlock(BaseModel):
    type: SafeBlockType
    text: str = Field(default="", max_length=4_000)
    items: list[str] = Field(default_factory=list, max_length=20)
    level: Literal[1, 2, 3] = 2

    @model_validator(mode="after")
    def validate_shape(self) -> GeneratedContentBlock:
        if self.type in {"bullet_list", "ordered_list"}:
            if not self.items:
                raise ValueError("List blocks require at least one item")
        elif self.type != "horizontal_rule" and not self.text.strip():
            raise ValueError("Text blocks require content")
        return self
