import asyncio
import json
from datetime import datetime, timezone

import httpx
import pytest
from bson import ObjectId
from pydantic import ValidationError

from app.config.config import ai_config
from app.core.exception import AIProviderUnavailableError, ContentRevisionConflictError
from app.schemas.content_suggestions import (
    GeneratedContentBlock,
    GeneratedLessonSuggestion,
    GeneratedModuleSuggestion,
    InstructionalPlan,
    LessonApplyRequest,
    LessonSuggestionRequest,
    ModuleApplyRequest,
    ModuleSuggestionRequest,
)
from app.services.content_suggestion_provider import DeepSeekContentSuggestionProvider, blocks_to_tiptap, get_content_suggestion_provider
from app.services.content_suggestion_service import (
    apply_lesson_suggestion,
    apply_module_suggestion,
    discard_revision,
    publish_revision,
)


def plan() -> InstructionalPlan:
    return InstructionalPlan.model_validate({
        "central_topic": "Comunicación profesional",
        "learning_objectives": ["Aplicar una estructura clara para presentar una idea."],
        "concept_map": {"label": "Comunicación", "children": [{"label": "Estructura", "children": []}]},
        "ordering_strategy": "simple_to_complex",
        "ordering_rationale": "Primero se construyen conceptos base y después se aplican en situaciones reales.",
        "recommended_formats": ["text", "activity"],
        "session_plan": [{"title": "Activación", "minutes": 10, "activity": "Relacionar el tema con una experiencia previa.", "format": "activity"}],
        "lesson_sequence": [{"key": "base", "title": "Conceptos base", "objective": "Reconocer los conceptos principales del tema.", "recommended_formats": ["text"], "source_id": None}],
    })


def lesson_document(module_id=None, status="draft"):
    lesson_id = ObjectId()
    return {
        "_id": lesson_id,
        "module_id": module_id or ObjectId(),
        "title": "Lección actual",
        "slug": "leccion-actual",
        "description": "Descripción actual",
        "content": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Contenido actual"}]}]},
        "media_assets": [],
        "order": 0,
        "status": status,
        "estimated_minutes": 20,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


class FakeModules:
    def __init__(self, document):
        self.document = document

    def find_by_id(self, value):
        return self.document if value == self.document["_id"] else None

    def update(self, value, changes):
        assert value == self.document["_id"]
        self.document.update(changes)
        self.document["updated_at"] = datetime.now(timezone.utc)
        return self.document


class FakeLessons:
    def __init__(self, documents):
        self.documents = {document["_id"]: document for document in documents}

    def list(self, module_id=None, status=None):
        return [document for document in self.documents.values() if module_id is None or document["module_id"] == module_id]

    def find_by_id(self, value):
        return self.documents.get(value)

    def update(self, value, changes):
        document = self.documents[value]
        document.update(changes)
        document["updated_at"] = datetime.now(timezone.utc)
        return document


class FakeRevisions:
    def __init__(self):
        self.documents = {}

    def find_pending(self, target_type, target_id):
        return next((document for document in self.documents.values() if document["target_type"] == target_type and document["target_id"] == target_id and document["status"] == "pending"), None)

    def create(self, document):
        value = {"_id": ObjectId(), "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "status": "pending", **document}
        self.documents[value["_id"]] = value
        return value

    def find_by_id(self, revision_id):
        return self.documents.get(revision_id)

    def update(self, revision_id, changes):
        document = self.documents[revision_id]
        document.update(changes)
        document["updated_at"] = datetime.now(timezone.utc)
        return document

    def mark(self, revision_id, status):
        return self.update(revision_id, {"status": status})

    def delete(self, revision_id):
        return self.documents.pop(revision_id, None)


class FakeProvider:
    provider_name = "fake"
    model_name = "fake-model"

    async def suggest_module(self, request, context):
        return GeneratedModuleSuggestion(title="Módulo sugerido", description="Descripción sugerida", instructional_plan=plan())

    async def suggest_lesson(self, request, context):
        return GeneratedLessonSuggestion(
            title="Lección sugerida",
            description="Descripción sugerida",
            estimated_minutes=25,
            instructional_plan=plan(),
            blocks=[GeneratedContentBlock(type="heading", text="Introducción"), GeneratedContentBlock(type="paragraph", text="Explicación editable.")],
        )


def test_safe_blocks_are_converted_to_tiptap_without_external_attributes():
    document = blocks_to_tiptap([
        GeneratedContentBlock(type="heading", text="Tema", level=2),
        GeneratedContentBlock(type="bullet_list", items=["Uno", "Dos"]),
    ])
    assert document["content"][0] == {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Tema"}]}
    assert "attrs" not in document["content"][1]


def test_invalid_generated_blocks_and_duplicate_blueprint_keys_are_rejected():
    with pytest.raises(ValidationError):
        GeneratedContentBlock(type="paragraph")
    with pytest.raises(ValidationError):
        InstructionalPlan.model_validate({**plan().model_dump(), "lesson_sequence": [
            {"key": "same", "title": "Uno", "objective": "Objetivo suficientemente largo.", "recommended_formats": ["text"]},
            {"key": "same", "title": "Dos", "objective": "Otro objetivo suficientemente largo.", "recommended_formats": ["text"]},
        ]})


def test_suggestion_limits_formats_and_module_metadata_selection_are_validated():
    with pytest.raises(ValidationError):
        ModuleSuggestionRequest(topic="Tema", lesson_count=13)
    with pytest.raises(ValidationError):
        InstructionalPlan.model_validate({**plan().model_dump(), "recommended_formats": ["podcast"]})
    with pytest.raises(ValidationError):
        ModuleApplyRequest(base_updated_at=datetime.now(timezone.utc), plan_sections=["fields"], instructional_plan=plan())


def test_module_and_lesson_generation_uses_context_without_persisting_a_suggestion():
    module_id = ObjectId()
    module = {"_id": module_id, "title": "Módulo", "slug": "modulo", "description": "Descripción", "status": "draft", "order": 0, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    lesson = lesson_document(module_id)
    modules = FakeModules(module)
    lessons = FakeLessons([lesson])
    from app.services.content_suggestion_service import generate_lesson_suggestion, generate_module_suggestion

    module_result = asyncio.run(generate_module_suggestion(modules, lessons, ModuleSuggestionRequest(topic="Comunicación"), FakeProvider()))
    lesson_result = asyncio.run(generate_lesson_suggestion(modules, lessons, LessonSuggestionRequest(topic="Comunicación"), FakeProvider()))
    assert module_result.provider == "fake"
    assert lesson_result.content is not None
    assert module.get("instructional_plan") is None


def test_draft_module_application_updates_selected_plan_and_order():
    module_id = ObjectId()
    module = {"_id": module_id, "title": "Módulo", "slug": "modulo", "description": "Descripción", "status": "draft", "order": 0, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    lesson = lesson_document(module_id)
    modules, lessons, revisions = FakeModules(module), FakeLessons([lesson]), FakeRevisions()
    request = ModuleApplyRequest(base_updated_at=module["updated_at"], plan_sections=["objectives", "lesson_sequence"], instructional_plan=plan(), lesson_orders=[{"lesson_id": str(lesson["_id"]), "order": 3}])

    result = asyncio.run(apply_module_suggestion(modules, lessons, revisions, str(module_id), request, {"_id": ObjectId()}))

    assert result["outcome"] == "updated"
    assert module["instructional_plan"]["learning_objectives"] == plan().learning_objectives
    assert lesson["order"] == 3


def test_draft_application_preserves_unselected_instructional_sections():
    module_id = ObjectId()
    existing_plan = {**plan().model_dump(), "recommended_formats": ["video"]}
    now = datetime.now(timezone.utc)
    module = {"_id": module_id, "title": "Módulo", "slug": "modulo", "description": "Descripción", "status": "draft", "instructional_plan": existing_plan, "created_at": now, "updated_at": now}
    modules, lessons, revisions = FakeModules(module), FakeLessons([]), FakeRevisions()
    request = ModuleApplyRequest(base_updated_at=module["updated_at"], plan_sections=["objectives"], instructional_plan=plan())

    asyncio.run(apply_module_suggestion(modules, lessons, revisions, str(module_id), request, {"_id": ObjectId()}))

    assert module["instructional_plan"]["learning_objectives"] == plan().learning_objectives
    assert module["instructional_plan"]["recommended_formats"] == ["video"]


def test_published_lesson_application_creates_revision_without_mutating_published_content():
    lesson = lesson_document(status="published")
    lessons, revisions = FakeLessons([lesson]), FakeRevisions()
    original_content = lesson["content"]
    request = LessonApplyRequest(base_updated_at=lesson["updated_at"], sections=["content", "objectives"], title="Nuevo", description="Nueva", estimated_minutes=30, instructional_plan=plan(), content={"type": "doc", "content": []})

    result = asyncio.run(apply_lesson_suggestion(lessons, revisions, str(lesson["_id"]), request, {"_id": ObjectId()}))

    assert result["outcome"] == "revision_created"
    assert lesson["content"] == original_content
    assert len(revisions.documents) == 1


def test_pending_lesson_revision_can_be_published_or_discarded_explicitly():
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

    result = asyncio.run(apply_lesson_suggestion(lessons, revisions, str(lesson["_id"]), request, {"_id": ObjectId()}))
    revision_id = next(iter(revisions.documents))
    published = asyncio.run(publish_revision(revisions, FakeModules({"_id": lesson["module_id"]}), lessons, str(revision_id), {"_id": ObjectId()}))

    assert published["outcome"] == "updated"
    assert lesson["content"] == {"type": "doc", "content": []}
    assert revisions.documents[revision_id]["status"] == "published"

    lesson = lesson_document(status="published")
    lessons, revisions = FakeLessons([lesson]), FakeRevisions()
    request = request.model_copy(update={"base_updated_at": lesson["updated_at"]})
    asyncio.run(apply_lesson_suggestion(lessons, revisions, str(lesson["_id"]), request, {"_id": ObjectId()}))
    revision_id = next(iter(revisions.documents))
    discarded = discard_revision(revisions, str(revision_id))

    assert discarded["status"] == "discarded"
    assert revision_id not in revisions.documents
    assert lesson["content"] != {"type": "doc", "content": []}


def test_application_rejects_stale_base_timestamp():
    module_id = ObjectId()
    module = {"_id": module_id, "title": "Módulo", "description": "Descripción", "status": "draft", "updated_at": datetime.now(timezone.utc)}
    request = ModuleApplyRequest(base_updated_at=datetime.now(timezone.utc), plan_sections=["objectives"], instructional_plan=plan())

    with pytest.raises(ContentRevisionConflictError):
        asyncio.run(apply_module_suggestion(FakeModules(module), FakeLessons([]), FakeRevisions(), str(module_id), request, {"_id": ObjectId()}))


class FakeResponse:
    def __init__(self, content, error=None):
        self.content = content
        self.error = error

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeAsyncClient:
    response = None
    post_error = None
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        if self.post_error:
            raise self.post_error
        return self.response


@pytest.fixture(autouse=True)
def provider_config(monkeypatch):
    monkeypatch.setitem(ai_config, "CONTENT_PROVIDER", "deepseek")
    monkeypatch.setitem(ai_config, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setitem(ai_config, "DEEPSEEK_BASE_URL", "https://deepseek.test")
    monkeypatch.setitem(ai_config, "DEEPSEEK_CONTENT_MODEL", "content-model")
    monkeypatch.setitem(ai_config, "DEEPSEEK_TIMEOUT_SECONDS", 7)
    FakeAsyncClient.calls = []
    FakeAsyncClient.post_error = None


def test_provider_validates_fenced_json_and_redacts_identifiers(monkeypatch):
    FakeAsyncClient.response = FakeResponse(f"```json\n{json.dumps({'title': 'Módulo', 'description': 'Descripción', 'instructional_plan': plan().model_dump()})}\n```")
    monkeypatch.setattr("app.services.content_suggestion_provider.httpx.AsyncClient", FakeAsyncClient)

    request = ModuleSuggestionRequest(
        topic="Tema",
        description="Correo test@example.com y teléfono 300 123 4567",
        lessons=[{"title": "Base", "description": "Contacto: persona@example.com"}],
    )
    result = asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(request, "Contexto"))

    assert result.title == "Módulo"
    prompt = FakeAsyncClient.calls[0]["kwargs"]["json"]["messages"][1]["content"]
    assert "test@example.com" not in prompt
    assert "300 123 4567" not in prompt


def test_provider_rejects_missing_key_or_invalid_json(monkeypatch):
    monkeypatch.setitem(ai_config, "DEEPSEEK_API_KEY", "")
    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(ModuleSuggestionRequest(topic="Tema"), ""))

    FakeAsyncClient.response = FakeResponse(json.dumps({"title": "Incompleto"}))
    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(ModuleSuggestionRequest(topic="Tema"), ""))


def test_provider_factory_rejects_unknown_provider(monkeypatch):
    monkeypatch.setitem(ai_config, "CONTENT_PROVIDER", "unknown")
    with pytest.raises(AIProviderUnavailableError):
        get_content_suggestion_provider()


def test_provider_wraps_timeout_and_http_errors(monkeypatch):
    monkeypatch.setattr("app.services.content_suggestion_provider.httpx.AsyncClient", FakeAsyncClient)
    FakeAsyncClient.post_error = httpx.TimeoutException("timed out")
    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(ModuleSuggestionRequest(topic="Tema"), ""))

    FakeAsyncClient.post_error = httpx.HTTPError("upstream failed")
    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(ModuleSuggestionRequest(topic="Tema"), ""))

    monkeypatch.setitem(ai_config, "DEEPSEEK_API_KEY", "test-key")
    FakeAsyncClient.response = FakeResponse("not-json")
    monkeypatch.setattr("app.services.content_suggestion_provider.httpx.AsyncClient", FakeAsyncClient)
    with pytest.raises(AIProviderUnavailableError):
        asyncio.run(DeepSeekContentSuggestionProvider().suggest_module(ModuleSuggestionRequest(topic="Tema"), ""))
