import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from fastapi import FastAPI

from app.core.exception import AuthorizationError, AssessmentUnavailableError, ConflictError, NotFoundError, register_exception_handlers
from app.middlewares.role_middleware import require_roles
from app.routes.assessment_routes import (
    analytics_overview,
    analytics_students,
    assign_trainer,
    approve_question,
    begin_attempt,
    create_lesson_assessment,
    create_module_assessment,
    educator_assessment,
    edit_assessment,
    edit_question,
    generate_suggestions,
    get_assessment_settings,
    invite_trainer,
    lesson_assessment,
    list_students,
    list_trainers,
    my_analytics,
    module_assessment,
    my_assessment_attempts,
    my_assessment_results,
    add_question,
    reset_student_attempts,
    student_analytics,
    submit,
    update_user_role,
    update_assessment_settings,
    _target_context,
)
from app.routes.content_routes import complete
from app.schemas.assessment import AssessmentSettingsUpdate, AssessmentUpdateRequest, AttemptSubmitRequest, GenerateSuggestionsRequest, QuestionCreateRequest, QuestionUpdateRequest, RoleUpdateRequest, TrainerInvitationRequest, TrainerAssignmentRequest
from app.services.question_provider import GeneratedQuestion
from tests.test_assessment_service import FakeAssessmentRepository, FakeLessons, FakeProgress


class FakeUsers:
    def __init__(self, documents):
        self.documents = {document["_id"]: document for document in documents}

    def find_by_id(self, user_id):
        return self.documents.get(user_id)

    def list_by_role(self, role):
        return [document for document in self.documents.values() if document.get("role") == role]

    def list_by_ids(self, ids):
        return [self.documents[user_id] for user_id in ids if user_id in self.documents]

    def create(self, document):
        created = {"_id": ObjectId(), **document}
        self.documents[created["_id"]] = created
        return created

    def find_by_email(self, email):
        return next((document for document in self.documents.values() if document["email"] == email), None)

    def update(self, user_id, changes):
        self.documents[user_id].update(changes)
        return self.documents[user_id]


def user(role):
    user_id = ObjectId()
    return {"_id": user_id, "email": f"{role}-{user_id}@example.com", "full_name": role.title(), "role": role, "is_active": True, "email_verified": True, "created_at": datetime.now(timezone.utc)}


def prepare_admin_questions(repository):
    now = datetime.now(timezone.utc)
    for question in repository.questions:
        question.update({"assessment_id": repository.assessment_id, "created_at": now, "updated_at": now})


def test_student_contract_hides_answers_and_invalid_attempt_ids_are_not_internal_errors():
    student = user("user")
    repository = FakeAssessmentRepository()
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])

    assessment = lesson_assessment(str(repository.assessment["target_id"]), user=student, assessments=repository, progress=progress, lessons=lessons)
    assert assessment["questions"] == []
    assert "correct_option_id" not in assessment

    with pytest.raises(NotFoundError) as caught:
        submit("not-an-object-id", AttemptSubmitRequest(answers=[{"question_id": "question", "selected_option_id": "a"}]), user=student, assessments=repository, progress=progress, lessons=lessons)
    assert caught.value.status_code == 404


def test_student_attempt_result_history_and_module_assessment_routes():
    student = user("user")
    repository = FakeAssessmentRepository()
    repository.assessment["question_count"] = 3
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])

    attempt = begin_attempt(str(repository.assessment_id), user=student, assessments=repository, progress=progress, lessons=lessons)
    result = submit(str(attempt["id"]), AttemptSubmitRequest(answers=[{"question_id": question["id"], "selected_option_id": "a"} for question in attempt["questions"]]), user=student, assessments=repository, progress=progress, lessons=lessons)
    assert result["passed"] is True
    assert len(my_assessment_results(user=student, assessments=repository)) == 1
    assert len(my_assessment_attempts(str(repository.assessment_id), user=student, assessments=repository)) == 1

    module_id = ObjectId()
    repository.assessment.update({"target_type": "module", "target_id": module_id})
    module_lessons = [{"_id": ObjectId(), "module_id": module_id}, {"_id": ObjectId(), "module_id": module_id}]
    progress.completed = [{"lesson_id": lesson["_id"], "module_id": module_id, "completion_source": "quiz"} for lesson in module_lessons]
    module_lessons_repository = FakeLessons(module_lessons[0]["_id"], module_id, module_lessons)
    module_payload = module_assessment(str(module_id), user=student, assessments=repository, progress=progress, lessons=module_lessons_repository)
    assert module_payload["target_type"] == "module"


def test_role_dependency_distinguishes_student_trainer_and_admin():
    admin_only = require_roles("admin")
    educator = require_roles("admin", "trainer")

    assert admin_only(user("admin"))["role"] == "admin"
    assert educator(user("trainer"))["role"] == "trainer"
    with pytest.raises(AuthorizationError):
        educator(user("user"))
    with pytest.raises(AuthorizationError):
        admin_only(user("trainer"))


def test_educator_can_read_answer_key_but_settings_are_an_admin_contract():
    trainer = user("trainer")
    repository = FakeAssessmentRepository()
    prepare_admin_questions(repository)

    response = educator_assessment(str(repository.assessment_id), trainer, repository)
    assert response["questions"][0]["correct_option_id"] == "a"

    with pytest.raises(AuthorizationError):
        require_roles("admin")(trainer)
    settings = get_assessment_settings(user("admin"), repository)
    assert settings["max_attempts"] == 3


def test_educator_can_create_edit_publish_and_approve_both_assessment_targets():
    trainer = user("trainer")
    repository = FakeAssessmentRepository()
    repository.assessment = None
    repository.questions = []
    lesson_id, module_id = ObjectId(), ObjectId()
    lesson_target = {"_id": lesson_id, "module_id": module_id, "title": "Lección", "description": "Descripción", "content": {"type": "doc", "content": []}}
    module_target = {"_id": module_id, "title": "Módulo", "description": "Descripción"}
    lessons = SimpleNamespace(find_by_id=lambda value: lesson_target if value == lesson_id else None, list=lambda *_args, **_kwargs: [lesson_target])
    modules = SimpleNamespace(find_by_id=lambda value: module_target if value == module_id else None)

    lesson_assessment_response = create_lesson_assessment(str(lesson_id), user=trainer, assessments=repository, modules=modules, lessons=lessons)
    assert lesson_assessment_response["target_type"] == "lesson"
    repository.assessment = None
    repository.questions = []
    module_assessment_response = create_module_assessment(str(module_id), user=trainer, assessments=repository, modules=modules, lessons=lessons)
    assert module_assessment_response["target_type"] == "module"

    question_payload = QuestionCreateRequest(
        prompt="¿Qué demuestra comprensión?",
        options=[{"id": value, "text": value} for value in ["a", "b", "c", "d"]],
        correct_option_id="a",
    )
    question = add_question(str(repository.assessment_id), question_payload, user=trainer, assessments=repository)
    edited = edit_question(str(question["id"]), QuestionUpdateRequest(competency="Aplicación"), trainer, repository)
    approved = approve_question(str(question["id"]), trainer, repository)
    assessment = edit_assessment(str(repository.assessment_id), AssessmentUpdateRequest(title="Evaluación final"), trainer, repository)
    assert edited["competency"] == "Aplicación"
    assert approved["status"] == "approved"
    assert assessment["title"] == "Evaluación final"


def test_admin_lists_people_resets_cycles_and_admin_analytics_include_all_students():
    admin = user("admin")
    trainer = user("trainer")
    student = user("user")
    users = FakeUsers([admin, trainer, student])
    repository = FakeAssessmentRepository()
    prepare_admin_questions(repository)
    repository.attempts.append({"_id": ObjectId(), "user_id": student["_id"], "assessment_id": repository.assessment_id, "status": "submitted", "score": 90, "passed": True, "attempt_number": 1, "cycle": 1, "answers": [{"is_correct": True, "competency": "Aplicación"}], "submitted_at": datetime.now(timezone.utc)})

    assert list_trainers(admin, users)[0]["role"] == "trainer"
    assert list_students(admin, users)[0]["role"] == "user"
    reset = reset_student_attempts(str(repository.assessment_id), str(student["_id"]), reason="Reforzar", admin_user=admin, assessments=repository)
    assert reset["cycle"] == 2

    overview = analytics_overview(educator_user=admin, assessments=repository, users=users)
    assert overview["students"] == 1
    students = analytics_students(educator_user=admin, assessments=repository, users=users)
    assert students[0]["attempts"] == 1


def test_route_missing_resource_and_provider_context_branches_are_controlled():
    repository = FakeAssessmentRepository()
    student = user("user")
    progress = FakeProgress()
    lessons = FakeLessons(repository.assessment["target_id"])

    with pytest.raises(NotFoundError):
        submit(str(ObjectId()), AttemptSubmitRequest(answers=[{"question_id": "question", "selected_option_id": "a"}]), user=student, assessments=repository, progress=progress, lessons=lessons)
    with pytest.raises(NotFoundError):
        educator_assessment(str(ObjectId()), student, repository)
    with pytest.raises(NotFoundError):
        asyncio.run(generate_suggestions(str(ObjectId()), GenerateSuggestionsRequest(count=3), user=student, assessments=repository, modules=SimpleNamespace(), lessons=SimpleNamespace()))
    with pytest.raises(NotFoundError):
        create_lesson_assessment(str(ObjectId()), user=student, assessments=repository, modules=SimpleNamespace(), lessons=SimpleNamespace(find_by_id=lambda _id: None))
    with pytest.raises(NotFoundError):
        create_module_assessment(str(ObjectId()), user=student, assessments=repository, modules=SimpleNamespace(find_by_id=lambda _id: None), lessons=SimpleNamespace())

    module_id = ObjectId()
    module_assessment = {"target_type": "module", "target_id": module_id}
    modules = SimpleNamespace(find_by_id=lambda _id: {"_id": module_id, "title": "Módulo", "description": "Descripción"})
    module_lessons = SimpleNamespace(list=lambda _id: [{"content": {"type": "doc", "content": [{"text": "Tema"}]}}])
    assert _target_context(module_assessment, modules, module_lessons)[2] == "Tema"
    with pytest.raises(NotFoundError):
        _target_context({"target_type": "lesson", "target_id": ObjectId()}, SimpleNamespace(), SimpleNamespace(find_by_id=lambda _id: None))


def test_invitation_and_role_update_failures_are_not_silent():
    admin = user("admin")
    existing = user("user")

    class MissingAfterCreateUsers(FakeUsers):
        def find_by_email(self, _email):
            return None

    with pytest.raises(NotFoundError):
        asyncio.run(invite_trainer(TrainerInvitationRequest(full_name="Trainer", email="missing@example.com", password="strong-password"), users=MissingAfterCreateUsers([admin]), account_email=SimpleNamespace(send_verification=AsyncMock())))

    class NullUpdateUsers(FakeUsers):
        def update(self, _user_id, _changes):
            return None

    with pytest.raises(NotFoundError):
        update_user_role(str(existing["_id"]), RoleUpdateRequest(role="trainer"), admin, NullUpdateUsers([existing]))

    class ConflictUsers(FakeUsers):
        def create(self, _document):
            raise __import__("pymongo").errors.DuplicateKeyError("duplicate")

    with pytest.raises(ConflictError):
        asyncio.run(invite_trainer(TrainerInvitationRequest(full_name="Trainer", email="duplicate@example.com", password="strong-password"), users=ConflictUsers([admin]), account_email=SimpleNamespace(send_verification=AsyncMock())))


def test_student_analytics_missing_user_is_not_exposed():
    admin = user("admin")
    repository = FakeAssessmentRepository()
    with pytest.raises(NotFoundError):
        student_analytics(str(ObjectId()), educator_user=admin, assessments=repository, users=FakeUsers([admin]))


def test_admin_settings_validation_and_manual_completion_contracts_are_enforced():
    repository = FakeAssessmentRepository()
    with pytest.raises(Exception):
        AssessmentSettingsUpdate(passing_score=101)

    repository.settings["passing_score"] = 90
    settings = update_assessment_settings(AssessmentSettingsUpdate(passing_score=90, default_question_count=3), user("admin"), repository)
    assert settings["passing_score"] == 90
    assert settings["default_question_count"] == 3
    assert settings["max_attempts"] == 3

    with pytest.raises(AssessmentUnavailableError) as caught:
        complete(str(repository.assessment["target_id"]), user("user"))
    assert caught.value.status_code == 409


def test_trainer_analytics_are_scoped_to_assigned_students_and_group_failures():
    trainer = user("trainer")
    assigned_student = user("user")
    outsider = user("user")
    users = FakeUsers([trainer, assigned_student, outsider])
    repository = FakeAssessmentRepository()
    repository.assignments[assigned_student["_id"]] = {"trainer_id": trainer["_id"]}
    repository.attempts.append({
        "_id": ObjectId(),
        "user_id": assigned_student["_id"],
        "assessment_id": repository.assessment_id,
        "status": "submitted",
        "score": 66.7,
        "answers": [{"is_correct": False, "competency": "Comunicación"}],
        "attempt_number": 1,
        "cycle": 1,
        "submitted_at": datetime.now(timezone.utc),
    })

    overview = analytics_overview(educator_user=trainer, assessments=repository, users=users)
    assert overview["students"] == 1
    assert overview["failed_competencies"] == [{"competency": "Comunicación", "count": 1}]

    allowed = student_analytics(str(assigned_student["_id"]), educator_user=trainer, assessments=repository, users=users)
    assert allowed["student_id"] == str(assigned_student["_id"])
    with pytest.raises(AuthorizationError):
        student_analytics(str(outsider["_id"]), educator_user=trainer, assessments=repository, users=users)


def test_student_analytics_endpoint_returns_period_series_from_private_events():
    student = user("user")
    repository = FakeAssessmentRepository()
    now = datetime.now(timezone.utc)
    lesson_id = repository.assessment["target_id"]
    module_id = ObjectId()
    progress = FakeProgress()
    progress.completed = [{"user_id": student["_id"], "lesson_id": lesson_id, "module_id": module_id, "completed_at": now}]
    lessons = FakeLessons(lesson_id, module_id)
    repository.attempts.append({
        "_id": ObjectId(),
        "user_id": student["_id"],
        "assessment_id": repository.assessment_id,
        "status": "submitted",
        "score": 90,
        "passed": True,
        "attempt_number": 1,
        "cycle": 1,
        "answers": [],
        "submitted_at": now,
    })

    payload = my_analytics(period="all", user=student, assessments=repository, progress=progress, lessons=lessons)

    assert payload["student_id"] == str(student["_id"])
    assert payload["attempts_count"] == 1
    assert payload["average_score"] == 90
    assert payload["activity_series"][0]["total"] == 2


def test_generate_suggestions_persists_actual_provider_metadata(monkeypatch):
    repository = FakeAssessmentRepository()
    prepare_admin_questions(repository)
    actor = user("trainer")

    class FakeProvider:
        provider_name = "fake-provider"
        model_name = "fake-model"

        async def generate(self, **_kwargs):
            return [GeneratedQuestion.model_validate({
                "prompt": "¿Qué demuestra comprensión del contenido?",
                "options": [{"id": option, "text": option} for option in ["a", "b", "c", "d"]],
                "correct_option_id": "a",
                "explanation": "Porque aplica el contenido.",
                "competency": "Comprensión",
                "difficulty": "basic",
            })]

    monkeypatch.setattr("app.routes.assessment_routes.get_question_provider", lambda: FakeProvider())
    modules = SimpleNamespace(find_by_id=lambda _id: {"_id": _id, "title": "Módulo", "description": "Descripción"})
    lessons = SimpleNamespace(list=lambda *_args, **_kwargs: [], find_by_id=lambda _id: {"_id": _id, "title": "Lección", "description": "Descripción", "content": {"type": "doc", "content": []}})

    result = asyncio.run(generate_suggestions(
        str(repository.assessment_id),
        GenerateSuggestionsRequest(count=3),
        user=actor,
        assessments=repository,
        modules=modules,
        lessons=lessons,
    ))

    assert result[0]["status"] == "suggested"
    assert result[0]["source_provider"] == "fake-provider"
    assert result[0]["source_model"] == "fake-model"


def test_admin_can_assign_trainer_invite_and_promote_without_allowing_admin_demotion():
    admin = user("admin")
    student = user("user")
    trainer = user("trainer")
    users = FakeUsers([admin, student, trainer])
    assignments = SimpleNamespace(assign_trainer=lambda student_id, trainer_id, admin_id: {"student_id": student_id, "trainer_id": trainer_id, "assigned_by": admin_id})

    assignment = assign_trainer(str(student["_id"]), TrainerAssignmentRequest(trainer_id=str(trainer["_id"])), admin_user=admin, assessments=assignments, users=users)
    assert assignment["trainer_id"] == trainer["_id"]

    with pytest.raises(AuthorizationError):
        assign_trainer(str(student["_id"]), TrainerAssignmentRequest(trainer_id=str(admin["_id"])), admin_user=admin, assessments=assignments, users=users)

    email_service = SimpleNamespace(send_verification=AsyncMock())
    invited = asyncio.run(invite_trainer(
        TrainerInvitationRequest(full_name="Nuevo Trainer", email="nuevo@example.com", password="strong-password"),
        users=users,
        account_email=email_service,
    ))
    assert invited["role"] == "trainer"
    email_service.send_verification.assert_awaited_once()

    promoted = update_user_role(str(student["_id"]), RoleUpdateRequest(role="trainer"), admin, users)
    assert promoted["role"] == "trainer"
    with pytest.raises(AuthorizationError):
        update_user_role(str(admin["_id"]), RoleUpdateRequest(role="user"), admin, users)


def test_assessment_router_exposes_all_contract_paths():
    app = FastAPI()
    register_exception_handlers(app)
    from app.routes.assessment_routes import router
    app.include_router(router)
    paths = set(app.openapi()["paths"])
    assert {
        "/assessments/lessons/{lesson_id}",
        "/assessments/modules/{module_id}",
        "/assessments/{assessment_id}/attempts",
        "/attempts/{attempt_id}/submit",
        "/me/assessment-results",
        "/educator/analytics/overview",
        "/educator/analytics/students/{student_id}",
        "/admin/assessment-settings",
        "/admin/trainers/invitations",
    } <= paths
