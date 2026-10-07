import json

import httpx
import pytest
from pydantic import ValidationError

from app.config.config import ai_config
from app.core.exception import AIProviderUnavailableError
from app.services.question_provider import DeepSeekQuestionProvider, GeneratedQuestion, get_question_provider, tiptap_to_text


def test_tiptap_to_text_extracts_only_educational_text():
    document = {"type": "doc", "content": [{"type": "heading", "content": [{"text": "CV"}]}, {"type": "paragraph", "content": [{"text": "Muestra logros medibles."}]}]}
    assert tiptap_to_text(document) == "CV Muestra logros medibles."


def test_tiptap_to_text_handles_lists_and_empty_nodes_without_leaking_metadata():
    document = [
        {"type": "paragraph", "content": [{"text": "Título"}]},
        {"type": "listItem", "content": [{"text": "Aplicar"}]},
        {"type": "image", "attrs": {"src": "https://private.example/cv.pdf"}},
    ]
    assert tiptap_to_text(document) == "Título Aplicar"


def test_generated_question_requires_four_options_and_valid_answer():
    question = GeneratedQuestion.model_validate({
        "prompt": "¿Qué demuestra mejor un logro profesional?",
        "options": [{"id": "a", "text": "Una actividad"}, {"id": "b", "text": "Un resultado"}, {"id": "c", "text": "Un horario"}, {"id": "d", "text": "Un cargo"}],
        "correct_option_id": "b",
        "explanation": "El resultado muestra impacto.",
        "competency": "Comunicación profesional",
        "difficulty": "intermediate",
    })
    assert question.correct_option_id == "b"

    with pytest.raises(ValidationError):
        GeneratedQuestion.model_validate({
            "prompt": "¿Qué demuestra mejor un logro profesional?",
            "options": [
                {"id": "a", "text": "Una actividad"},
                {"id": "a", "text": "Un resultado"},
                {"id": "c", "text": "Un horario"},
                {"id": "d", "text": "Un cargo"},
            ],
            "correct_option_id": "a",
        })


def generated_question(prompt="¿Qué opción aplica mejor el concepto?"):
    return {
        "prompt": prompt,
        "options": [
            {"id": "a", "text": "Aplicación correcta"},
            {"id": "b", "text": "Distractor uno"},
            {"id": "c", "text": "Distractor dos"},
            {"id": "d", "text": "Distractor tres"},
        ],
        "correct_option_id": "a",
        "explanation": "La aplicación correcta demuestra comprensión.",
        "competency": "Aplicación",
        "difficulty": "intermediate",
    }


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
    calls = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def post(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs, "timeout": self.kwargs["timeout"]})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


@pytest.fixture(autouse=True)
def reset_provider_config(monkeypatch):
    monkeypatch.setitem(ai_config, "DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setitem(ai_config, "DEEPSEEK_BASE_URL", "https://deepseek.test")
    monkeypatch.setitem(ai_config, "DEEPSEEK_MODEL", "test-model")
    monkeypatch.setitem(ai_config, "DEEPSEEK_TIMEOUT_SECONDS", 7)
    monkeypatch.setitem(ai_config, "PROVIDER", "deepseek")
    FakeAsyncClient.calls = []
    FakeAsyncClient.response = FakeResponse(json.dumps({"questions": [generated_question()]}))


def test_deepseek_provider_sends_openai_compatible_json_and_validates_response(monkeypatch):
    monkeypatch.setattr("app.services.question_provider.httpx.AsyncClient", FakeAsyncClient)

    questions = __import__("asyncio").run(DeepSeekQuestionProvider().generate(title="Tema", description="Descripción", content="Contenido educativo", count=1))

    assert questions[0].correct_option_id == "a"
    call = FakeAsyncClient.calls[0]
    assert call["url"] == "https://deepseek.test/chat/completions"
    assert call["timeout"] == 7
    assert call["kwargs"]["headers"]["Authorization"] == "Bearer test-key"
    assert call["kwargs"]["json"]["model"] == "test-model"
    assert call["kwargs"]["json"]["response_format"] == {"type": "json_object"}
    prompt = call["kwargs"]["json"]["messages"][1]["content"]
    assert "Contenido educativo" in prompt
    assert "test@example.com" not in prompt
    assert "teléfono" not in prompt.lower()


def test_deepseek_provider_accepts_fenced_json(monkeypatch):
    FakeAsyncClient.response = FakeResponse(f"```json\n{json.dumps({'questions': [generated_question()]})}\n```")
    monkeypatch.setattr("app.services.question_provider.httpx.AsyncClient", FakeAsyncClient)

    questions = __import__("asyncio").run(DeepSeekQuestionProvider().generate(title="Tema", description="", content="", count=1))

    assert len(questions) == 1


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse("not-json"),
        FakeResponse(json.dumps({"questions": []})),
        FakeResponse(json.dumps({"questions": [{**generated_question(), "options": [{"id": "a", "text": "Solo una"}]}]})),
        FakeResponse("", error=httpx.HTTPError("provider unavailable")),
    ],
)
def test_deepseek_provider_rejects_invalid_or_unavailable_responses(monkeypatch, response):
    FakeAsyncClient.response = response
    monkeypatch.setattr("app.services.question_provider.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(AIProviderUnavailableError):
        __import__("asyncio").run(DeepSeekQuestionProvider().generate(title="Tema", description="", content="", count=1))


def test_deepseek_provider_requires_server_side_key(monkeypatch):
    monkeypatch.setitem(ai_config, "DEEPSEEK_API_KEY", "")

    with pytest.raises(AIProviderUnavailableError):
        __import__("asyncio").run(DeepSeekQuestionProvider().generate(title="Tema", description="", content="", count=1))


def test_provider_factory_is_configurable_and_rejects_unknown_provider(monkeypatch):
    assert isinstance(get_question_provider(), DeepSeekQuestionProvider)
    monkeypatch.setitem(ai_config, "PROVIDER", "unknown")
    with pytest.raises(AIProviderUnavailableError):
        get_question_provider()
