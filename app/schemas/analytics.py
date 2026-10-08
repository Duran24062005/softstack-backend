from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


AnalyticsPeriod = Literal["7d", "30d", "90d", "all"]


class AnalyticsPoint(BaseModel):
    time: date
    value: float


class AnalyticsActivityPoint(BaseModel):
    time: date
    lessons_completed: int = Field(ge=0)
    modules_completed: int = Field(ge=0)
    assessments_submitted: int = Field(ge=0)
    total: int = Field(ge=0)


class AnalyticsSnapshot(BaseModel):
    completed_lessons: int = Field(ge=0)
    total_lessons: int = Field(ge=0)
    percentage: float = Field(ge=0, le=100)
    completed_modules: int = Field(ge=0)
    total_modules: int = Field(ge=0)
    module_percentage: float = Field(ge=0, le=100)


class AnalyticsPayload(BaseModel):
    period: AnalyticsPeriod
    snapshot: AnalyticsSnapshot
    active_students: int = Field(ge=0)
    average_score: float = Field(ge=0, le=100)
    progress_series: list[AnalyticsPoint] = Field(default_factory=list)
    score_series: list[AnalyticsPoint] = Field(default_factory=list)
    activity_series: list[AnalyticsActivityPoint] = Field(default_factory=list)
    failed_competencies: list[dict[str, int | str]] = Field(default_factory=list)


class MyAnalyticsResponse(AnalyticsPayload):
    student_id: str
    attempts_count: int = Field(ge=0)


class AnalyticsOverviewResponse(AnalyticsPayload):
    students: int = Field(ge=0)
    assigned_students: int = Field(ge=0)
    attempts: int = Field(ge=0)


class StudentAnalyticsResponse(AnalyticsPayload):
    student_id: str
    student_name: str
    trainer_id: str | None = None
    attempts: list[dict[str, object]] = Field(default_factory=list)
