from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


AssessmentTarget = Literal["lesson", "module"]
QuestionStatus = Literal["suggested", "approved", "archived"]


class QuestionOption(BaseModel):
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=500)


class QuestionCreateRequest(BaseModel):
    prompt: str = Field(min_length=10, max_length=1_000)
    options: list[QuestionOption] = Field(min_length=4, max_length=4)
    correct_option_id: str = Field(min_length=1, max_length=8)
    explanation: str = Field(default="", max_length=1_000)
    competency: str = Field(default="Comprensión del tema", min_length=2, max_length=120)
    difficulty: Literal["basic", "intermediate", "advanced"] = "intermediate"
    status: QuestionStatus = "suggested"

    @model_validator(mode="after")
    def validate_options(self):
        ids = [option.id for option in self.options]
        if len(set(ids)) != len(ids) or self.correct_option_id not in ids:
            raise ValueError("Question options must be unique and include the correct answer")
        return self


class QuestionUpdateRequest(BaseModel):
    prompt: str | None = Field(default=None, min_length=10, max_length=1_000)
    options: list[QuestionOption] | None = Field(default=None, min_length=4, max_length=4)
    correct_option_id: str | None = Field(default=None, min_length=1, max_length=8)
    explanation: str | None = Field(default=None, max_length=1_000)
    competency: str | None = Field(default=None, min_length=2, max_length=120)
    difficulty: Literal["basic", "intermediate", "advanced"] | None = None
    status: QuestionStatus | None = None


class QuestionPublicResponse(BaseModel):
    id: str
    prompt: str
    options: list[QuestionOption]
    competency: str
    difficulty: str


class QuestionAdminResponse(QuestionPublicResponse):
    assessment_id: str
    correct_option_id: str
    explanation: str
    status: QuestionStatus
    source_provider: str | None = None
    source_model: str | None = None
    created_at: datetime
    updated_at: datetime


class AssessmentSettingsResponse(BaseModel):
    passing_score: int = Field(ge=1, le=100)
    max_attempts: Literal[3] = 3
    default_question_count: int = Field(ge=3, le=5)


class AssessmentSettingsUpdate(BaseModel):
    passing_score: int | None = Field(default=None, ge=1, le=100)
    default_question_count: int | None = Field(default=None, ge=3, le=5)


class AssessmentUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    question_count: int | None = Field(default=None, ge=3, le=5)
    status: Literal["draft", "published", "archived"] | None = None


class AssessmentResponse(BaseModel):
    id: str
    target_type: AssessmentTarget
    target_id: str
    title: str
    status: str
    question_count: int = Field(ge=3, le=5)
    passing_score: int = Field(ge=1, le=100)
    max_attempts: Literal[3] = 3
    approved_question_count: int
    attempts_used: int = 0
    attempts_remaining: int = 3
    passed: bool = False
    locked: bool = False
    lock_reason: str | None = None
    questions: list[QuestionPublicResponse] = Field(default_factory=list)


class AssessmentAdminResponse(AssessmentResponse):
    questions: list[QuestionAdminResponse] = Field(default_factory=list)


class AttemptStartResponse(BaseModel):
    id: str
    assessment_id: str
    attempt_number: int
    cycle: int
    questions: list[QuestionPublicResponse]
    attempts_remaining: int


class AttemptAnswerRequest(BaseModel):
    question_id: str
    selected_option_id: str


class AttemptSubmitRequest(BaseModel):
    answers: list[AttemptAnswerRequest] = Field(min_length=1, max_length=5)


class AttemptQuestionResult(BaseModel):
    question_id: str
    selected_option_id: str
    correct_option_id: str
    is_correct: bool
    explanation: str
    competency: str


class AttemptResultResponse(BaseModel):
    id: str
    assessment_id: str
    attempt_number: int
    cycle: int
    score: float
    passed: bool
    attempts_used: int
    attempts_remaining: int
    question_results: list[AttemptQuestionResult]
    lesson_completed: bool = False
    module_completed: bool = False
    submitted_at: datetime


class AssessmentAttemptSummary(BaseModel):
    id: str
    assessment_id: str
    attempt_number: int
    cycle: int
    score: float
    passed: bool
    submitted_at: datetime


class GenerateSuggestionsRequest(BaseModel):
    count: int = Field(default=5, ge=3, le=10)


class TrainerAssignmentRequest(BaseModel):
    trainer_id: str


class TrainerInvitationRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "trainer"]
