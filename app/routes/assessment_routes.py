from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status

from app.config.config import assessment_config
from app.core.exception import AuthorizationError, NotFoundError
from app.core.exception import ConflictError
from app.middlewares.role_middleware import require_roles
from app.models.auth import public_user
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository
from app.repositories.user_repository import UserRepository
from app.routes.content_dependencies import get_assessment_repository, get_lesson_repository, get_module_repository, get_progress_repository
from app.routes.dependencies import current_user, get_user_repository
from app.schemas.assessment import (
    AssessmentAdminResponse,
    AssessmentResponse,
    AssessmentSettingsResponse,
    AssessmentSettingsUpdate,
    AssessmentUpdateRequest,
    AttemptResultResponse,
    AttemptStartResponse,
    AttemptSubmitRequest,
    GenerateSuggestionsRequest,
    QuestionAdminResponse,
    QuestionCreateRequest,
    QuestionUpdateRequest,
    StudentAnalyticsResponse,
    TrainerAssignmentRequest,
    TrainerInvitationRequest,
    RoleUpdateRequest,
)
from app.services.auth_service import register_user
from app.services.account_email_service import AccountEmailService
from app.routes.dependencies import get_account_email_service
from app.services.assessment_service import (
    create_question,
    ensure_assessment,
    get_admin_assessment,
    get_student_assessment,
    list_attempt_summaries,
    parse_id,
    start_attempt,
    submit_attempt,
    update_assessment,
    update_question,
)
from app.services.question_provider import get_question_provider, tiptap_to_text

router = APIRouter(tags=["assessments"])
educator = require_roles("admin", "trainer")
admin = require_roles("admin")


def _target_context(assessment: dict[str, Any], modules: ModuleRepository, lessons: LessonRepository) -> tuple[str, str, str]:
    target = modules.find_by_id(assessment["target_id"]) if assessment["target_type"] == "module" else lessons.find_by_id(assessment["target_id"])
    if not target:
        raise NotFoundError
    content = target.get("content", {})
    if assessment["target_type"] == "module":
        content = " ".join(tiptap_to_text(lesson.get("content", {})) for lesson in lessons.list(assessment["target_id"]))
    else:
        content = tiptap_to_text(content)
    return target.get("title", ""), target.get("description", ""), content


@router.get("/assessments/lessons/{lesson_id}", response_model=AssessmentResponse)
def lesson_assessment(lesson_id: str, user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository), progress: ProgressRepository = Depends(get_progress_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    return get_student_assessment(assessments, "lesson", lesson_id, progress, lessons, user)


@router.get("/assessments/modules/{module_id}", response_model=AssessmentResponse)
def module_assessment(module_id: str, user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository), progress: ProgressRepository = Depends(get_progress_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    return get_student_assessment(assessments, "module", module_id, progress, lessons, user)


@router.post("/assessments/{assessment_id}/attempts", response_model=AttemptStartResponse)
def begin_attempt(assessment_id: str, user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository), progress: ProgressRepository = Depends(get_progress_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    return start_attempt(assessments, assessment_id, progress, lessons, user)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResultResponse)
def submit(attempt_id: str, payload: AttemptSubmitRequest, user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository), progress: ProgressRepository = Depends(get_progress_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    attempt = assessments.find_attempt(parse_id(attempt_id))
    if not attempt:
        raise NotFoundError
    return submit_attempt(assessments, str(attempt["assessment_id"]), attempt_id, payload.model_dump(), progress, lessons, user)


@router.get("/me/assessment-results", response_model=list)
def my_assessment_results(user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return list_attempt_summaries(assessments, user)


@router.get("/me/assessments/{assessment_id}/attempts", response_model=list)
def my_assessment_attempts(assessment_id: str, user=Depends(current_user), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return list_attempt_summaries(assessments, user, assessment_id)


@router.post("/educator/assessments/lessons/{lesson_id}", response_model=AssessmentAdminResponse, status_code=status.HTTP_201_CREATED)
def create_lesson_assessment(lesson_id: str, user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), modules: ModuleRepository = Depends(get_module_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    lesson = lessons.find_by_id(parse_id(lesson_id))
    if not lesson:
        raise NotFoundError
    assessment = ensure_assessment(assessments, "lesson", lesson_id, f"Evaluación: {lesson['title']}", user, modules, lessons)
    return get_admin_assessment(assessments, str(assessment["_id"]))


@router.post("/educator/assessments/modules/{module_id}", response_model=AssessmentAdminResponse, status_code=status.HTTP_201_CREATED)
def create_module_assessment(module_id: str, user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), modules: ModuleRepository = Depends(get_module_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    module = modules.find_by_id(parse_id(module_id))
    if not module:
        raise NotFoundError
    assessment = ensure_assessment(assessments, "module", module_id, f"Evaluación final: {module['title']}", user, modules, lessons)
    return get_admin_assessment(assessments, str(assessment["_id"]))


@router.get("/educator/assessments/{assessment_id}", response_model=AssessmentAdminResponse)
def educator_assessment(assessment_id: str, _: dict = Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return get_admin_assessment(assessments, assessment_id)


@router.patch("/educator/assessments/{assessment_id}", response_model=AssessmentAdminResponse)
def edit_assessment(assessment_id: str, payload: AssessmentUpdateRequest, _: dict = Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return update_assessment(assessments, assessment_id, payload.model_dump(exclude_unset=True))


@router.post("/educator/assessments/{assessment_id}/questions", response_model=QuestionAdminResponse, status_code=status.HTTP_201_CREATED)
def add_question(assessment_id: str, payload: QuestionCreateRequest, user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return create_question(assessments, assessment_id, payload.model_dump(), user)


@router.patch("/educator/questions/{question_id}", response_model=QuestionAdminResponse)
def edit_question(question_id: str, payload: QuestionUpdateRequest, _: dict = Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return update_question(assessments, question_id, payload.model_dump(exclude_unset=True))


@router.post("/educator/questions/{question_id}/approve", response_model=QuestionAdminResponse)
def approve_question(question_id: str, _: dict = Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return update_question(assessments, question_id, {"status": "approved"})


@router.post("/educator/assessments/{assessment_id}/generate-suggestions", response_model=list[QuestionAdminResponse])
async def generate_suggestions(assessment_id: str, payload: GenerateSuggestionsRequest, user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), modules: ModuleRepository = Depends(get_module_repository), lessons: LessonRepository = Depends(get_lesson_repository)):
    parsed_assessment_id = parse_id(assessment_id)
    assessment = assessments.find_assessment(parsed_assessment_id)
    if not assessment:
        raise NotFoundError
    title, description, content = _target_context(assessment, modules, lessons)
    provider = get_question_provider()
    generated = await provider.generate(title=title, description=description, content=content, count=payload.count)
    provider_name = getattr(provider, "provider_name", "unknown")
    model_name = getattr(provider, "model_name", None)
    return [create_question(assessments, assessment_id, {**question.model_dump(), "status": "suggested"}, user, provider_name, model_name) for question in generated]


@router.get("/admin/assessment-settings", response_model=AssessmentSettingsResponse)
def get_assessment_settings(_: dict = Depends(admin), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    settings = assessments.get_settings({"passing_score": assessment_config["DEFAULT_PASSING_SCORE"], "max_attempts": 3, "default_question_count": assessment_config["DEFAULT_QUESTION_COUNT"]})
    return {"passing_score": settings["passing_score"], "max_attempts": 3, "default_question_count": settings["default_question_count"]}


@router.patch("/admin/assessment-settings", response_model=AssessmentSettingsResponse)
def update_assessment_settings(payload: AssessmentSettingsUpdate, _: dict = Depends(admin), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    settings = assessments.update_settings(payload.model_dump(exclude_unset=True), {"passing_score": assessment_config["DEFAULT_PASSING_SCORE"], "max_attempts": 3, "default_question_count": assessment_config["DEFAULT_QUESTION_COUNT"]})
    return {"passing_score": settings["passing_score"], "max_attempts": 3, "default_question_count": settings["default_question_count"]}


@router.post("/admin/assessments/{assessment_id}/students/{student_id}/reset")
def reset_student_attempts(assessment_id: str, student_id: str, reason: str | None = None, admin_user=Depends(admin), assessments: AssessmentRepository = Depends(get_assessment_repository)):
    return assessments.reset_state(parse_id(student_id), parse_id(assessment_id), admin_user["_id"], reason)


@router.post("/admin/students/{student_id}/trainer")
def assign_trainer(student_id: str, payload: TrainerAssignmentRequest, admin_user=Depends(admin), assessments: AssessmentRepository = Depends(get_assessment_repository), users: UserRepository = Depends(get_user_repository)):
    student = users.find_by_id(parse_id(student_id))
    trainer = users.find_by_id(parse_id(payload.trainer_id))
    if not student or student.get("role") != "user" or not trainer or trainer.get("role") != "trainer":
        raise AuthorizationError
    return assessments.assign_trainer(student["_id"], trainer["_id"], admin_user["_id"])


@router.post("/admin/trainers/invitations")
async def invite_trainer(payload: TrainerInvitationRequest, _: dict = Depends(admin), users: UserRepository = Depends(get_user_repository), account_email: AccountEmailService = Depends(get_account_email_service)):
    try:
        created = register_user(users, payload.email, payload.password, payload.full_name)
    except ConflictError:
        raise
    user = users.find_by_email(payload.email.lower())
    if not user:
        raise NotFoundError
    updated = users.update(user["_id"], {"role": "trainer"})
    if updated:
        await account_email.send_verification(updated)
    return public_user(updated or users.find_by_email(payload.email.lower()))


@router.get("/admin/trainers")
def list_trainers(_: dict = Depends(admin), users: UserRepository = Depends(get_user_repository)):
    return [public_user(user) for user in users.list_by_role("trainer")]


@router.get("/admin/students")
def list_students(_: dict = Depends(admin), users: UserRepository = Depends(get_user_repository)):
    return [public_user(user) for user in users.list_by_role("user")]


@router.patch("/admin/users/{user_id}/role")
def update_user_role(user_id: str, payload: RoleUpdateRequest, _: dict = Depends(admin), users: UserRepository = Depends(get_user_repository)):
    target = users.find_by_id(parse_id(user_id))
    if not target or target.get("role") == "admin":
        raise AuthorizationError
    updated = users.update(target["_id"], {"role": payload.role})
    if not updated:
        raise NotFoundError
    return public_user(updated)


@router.get("/educator/analytics/overview")
def analytics_overview(educator_user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), users: UserRepository = Depends(get_user_repository)):
    student_ids = assessments.students_for_trainer(educator_user["_id"]) if educator_user.get("role") == "trainer" else [user["_id"] for user in users.list_by_role("user")]
    attempts = [attempt for attempt in assessments.list_attempts(student_ids=student_ids) if attempt.get("status") == "submitted"]
    competency_counts: dict[str, int] = {}
    for attempt in attempts:
        for answer in attempt.get("answers", []):
            if not answer.get("is_correct"):
                competency = answer.get("competency", "Sin clasificar")
                competency_counts[competency] = competency_counts.get(competency, 0) + 1
    scores = [float(attempt.get("score", 0)) for attempt in attempts]
    return {"students": len(student_ids), "assigned_students": len(student_ids), "attempts": len(attempts), "average_score": round(sum(scores) / len(scores), 1) if scores else 0, "failed_competencies": [{"competency": key, "count": value} for key, value in sorted(competency_counts.items(), key=lambda item: item[1], reverse=True)]}


@router.get("/educator/analytics/students")
def analytics_students(educator_user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), users: UserRepository = Depends(get_user_repository)):
    student_ids = assessments.students_for_trainer(educator_user["_id"]) if educator_user.get("role") == "trainer" else [user["_id"] for user in users.list_by_role("user")]
    students = users.list_by_ids(student_ids)
    result = []
    for student in students:
        attempts = [attempt for attempt in assessments.list_attempts(user_id=student["_id"]) if attempt.get("status") == "submitted"]
        scores = [float(attempt.get("score", 0)) for attempt in attempts]
        assignment = assessments.assignment_for_student(student["_id"])
        result.append({"id": str(student["_id"]), "full_name": student.get("full_name") or student["email"], "email": student["email"], "attempts": len(attempts), "average_score": round(sum(scores) / len(scores), 1) if scores else 0, "trainer_id": str(assignment["trainer_id"]) if assignment else None})
    return result


@router.get("/educator/analytics/students/{student_id}", response_model=StudentAnalyticsResponse)
def student_analytics(student_id: str, educator_user=Depends(educator), assessments: AssessmentRepository = Depends(get_assessment_repository), users: UserRepository = Depends(get_user_repository)):
    parsed = parse_id(student_id)
    if educator_user.get("role") == "trainer" and parsed not in assessments.students_for_trainer(educator_user["_id"]):
        raise AuthorizationError
    student = users.find_by_id(parsed)
    if not student:
        raise NotFoundError
    attempts = [attempt for attempt in assessments.list_attempts(user_id=parsed) if attempt.get("status") == "submitted"]
    competency_counts: dict[str, int] = {}
    for attempt in attempts:
        for answer in attempt.get("answers", []):
            if not answer.get("is_correct"):
                competency = answer.get("competency", "Sin clasificar")
                competency_counts[competency] = competency_counts.get(competency, 0) + 1
    return {"student_id": str(student["_id"]), "student_name": student.get("full_name") or student["email"], "trainer_id": (assessments.assignment_for_student(parsed) or {}).get("trainer_id"), "attempts": [{"id": str(attempt["_id"]), "assessment_id": str(attempt["assessment_id"]), "attempt_number": attempt["attempt_number"], "cycle": attempt["cycle"], "score": attempt.get("score", 0), "passed": bool(attempt.get("passed")), "submitted_at": attempt["submitted_at"]} for attempt in attempts], "failed_competencies": [{"competency": key, "count": value} for key, value in sorted(competency_counts.items(), key=lambda item: item[1], reverse=True)]}
