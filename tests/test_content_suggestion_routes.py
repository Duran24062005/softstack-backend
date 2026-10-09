import asyncio
from datetime import datetime, timezone

import pytest
from bson import ObjectId

from app.core.exception import AuthorizationError, NotFoundError
from app.middlewares.role_middleware import require_roles
from app.routes import content_suggestion_routes as routes
from app.schemas.content_suggestions import LessonApplyRequest, LessonSuggestionRequest, ModuleSuggestionRequest
from tests.test_content_suggestions import FakeLessons, FakeModules, FakeProvider, FakeRevisions, lesson_document, plan


def user(role):
    return {"_id": ObjectId(), "role": role, "email": f"{role}@example.com"}


def test_content_suggestion_role_contract_allows_admin_and_trainer_only():
    educator = require_roles("admin", "trainer")

    assert educator(user("admin"))["role"] == "admin"
    assert educator(user("trainer"))["role"] == "trainer"
    with pytest.raises(AuthorizationError):
        educator(user("user"))


def test_generation_routes_return_structured_module_and_lesson_proposals(monkeypatch):
    module_id = ObjectId()
    module = {"_id": module_id, "title": "Módulo", "description": "Descripción", "status": "draft", "updated_at": datetime.now(timezone.utc)}
    lesson = lesson_document(module_id)
    monkeypatch.setattr(routes, "get_content_suggestion_provider", lambda: FakeProvider())

    module_response = asyncio.run(routes.suggest_module(ModuleSuggestionRequest(topic="Tema"), user("trainer"), FakeModules(module), FakeLessons([lesson])))
    lesson_response = asyncio.run(routes.suggest_lesson(LessonSuggestionRequest(topic="Tema"), user("admin"), FakeModules(module), FakeLessons([lesson])))

    assert module_response.target_type == "module"
    assert module_response.instructional_plan.learning_objectives
    assert lesson_response.target_type == "lesson"
    assert lesson_response.content is not None


def test_revision_routes_support_pending_lookup_publish_and_discard():
    lesson = lesson_document(status="published")
    lessons, revisions = FakeLessons([lesson]), FakeRevisions()
    request = LessonApplyRequest(
        base_updated_at=lesson["updated_at"],
        sections=["content"],
        title=lesson["title"],
        description=lesson["description"],
        estimated_minutes=lesson["estimated_minutes"],
        instructional_plan=plan(),
        content={"type": "doc", "content": []},
    )
    applied = asyncio.run(routes.apply_lesson(str(lesson["_id"]), request, user("trainer"), lessons, revisions, None, None))
    revision_id = applied["revision"]["id"]

    pending = routes.pending_revision("lesson", str(lesson["_id"]), user("admin"), revisions)
    assert pending["id"] == revision_id

    published = asyncio.run(routes.publish(revision_id, user("admin"), revisions, FakeModules({"_id": lesson["module_id"]}), lessons, None, None))
    assert published["outcome"] == "updated"
    assert lesson["content"] == {"type": "doc", "content": []}

    with pytest.raises(NotFoundError):
        routes.pending_revision("lesson", str(lesson["_id"]), user("admin"), revisions)

    second = lesson_document(status="published")
    second_lessons = FakeLessons([second])
    second_request = request.model_copy(update={"base_updated_at": second["updated_at"]})
    applied = asyncio.run(routes.apply_lesson(str(second["_id"]), second_request, user("trainer"), second_lessons, revisions, None, None))
    discarded = routes.discard(applied["revision"]["id"], user("trainer"), revisions)
    assert discarded["status"] == "discarded"
    assert revisions.find_pending("lesson", second["_id"]) is None
