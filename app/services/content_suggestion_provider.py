from __future__ import annotations

import json
import re
from typing import Protocol

import httpx
from pydantic import ValidationError

from app.config.config import ai_config
from app.core.exception import AIProviderUnavailableError
from app.schemas.content_suggestions import (
    GeneratedLessonSuggestion,
    GeneratedModuleSuggestion,
    LessonSuggestionRequest,
    ModuleSuggestionRequest,
)
from app.services.content_text import tiptap_to_text


class ContentSuggestionProvider(Protocol):
    async def suggest_module(self, request: ModuleSuggestionRequest, context: str) -> GeneratedModuleSuggestion: ...

    async def suggest_lesson(self, request: LessonSuggestionRequest, context: str) -> GeneratedLessonSuggestion: ...


def _json_content(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s*```$", "", cleaned)


def _sanitize_text(value: str) -> str:
    value = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[correo omitido]", value)
    return re.sub(r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)", "[teléfono omitido]", value)


def blocks_to_tiptap(blocks) -> dict:
    content: list[dict] = []
    for block in blocks:
        if block.type == "horizontal_rule":
            content.append({"type": "horizontalRule"})
        elif block.type == "heading":
            content.append({"type": "heading", "attrs": {"level": block.level}, "content": [{"type": "text", "text": block.text.strip()}]})
        elif block.type == "paragraph":
            content.append({"type": "paragraph", "content": [{"type": "text", "text": block.text.strip()}]})
        elif block.type == "blockquote":
            content.append({"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": block.text.strip()}]}]})
        elif block.type == "code_block":
            content.append({"type": "codeBlock", "content": [{"type": "text", "text": block.text.strip()}]})
        else:
            content.append({
                "type": "bulletList" if block.type == "bullet_list" else "orderedList",
                "content": [
                    {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": item.strip()}]}]}
                    for item in block.items
                ],
            })
    return {"type": "doc", "content": content}


class DeepSeekContentSuggestionProvider:
    provider_name = "deepseek"

    @property
    def model_name(self) -> str:
        return ai_config["DEEPSEEK_CONTENT_MODEL"]

    async def _complete(self, prompt: str) -> dict:
        api_key = ai_config["DEEPSEEK_API_KEY"]
        if not api_key:
            raise AIProviderUnavailableError
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Eres un diseñador instruccional. Responde únicamente JSON válido y no inventes datos personales."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        }
        try:
            async with httpx.AsyncClient(timeout=ai_config["DEEPSEEK_TIMEOUT_SECONDS"]) as client:
                response = await client.post(
                    f"{ai_config['DEEPSEEK_BASE_URL']}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json=payload,
                )
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
            return json.loads(_json_content(raw))
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError, ValidationError, ValueError) as error:
            raise AIProviderUnavailableError from error

    async def suggest_module(self, request: ModuleSuggestionRequest, context: str) -> GeneratedModuleSuggestion:
        lessons = json.dumps([lesson.model_dump(exclude_none=True) for lesson in request.lessons], ensure_ascii=False)
        prompt = f"""
Diseña un blueprint instruccional para un módulo educativo.
Modo: {request.mode}. Tema central: {_sanitize_text(request.topic)}.
Título actual: {_sanitize_text(request.title)}. Descripción actual: {_sanitize_text(request.description)}.
Audiencia: {_sanitize_text(request.audience)}. Nivel: {_sanitize_text(request.level)}.
Número objetivo de lecciones: {request.lesson_count}.
Lecciones actuales: {_sanitize_text(lessons)}.
Contexto adicional: {_sanitize_text(context[:18_000])}.

Aplica estas reglas: define objetivos observables, organiza de simple a complejo o justifica otra estrategia,
construye un mapa conceptual jerárquico, recomienda formatos y crea una guía de sesión con tiempos.
Devuelve solo un JSON con title, description e instructional_plan. El plan debe incluir lesson_sequence con
exactamente {request.lesson_count} elementos cuando el modo sea create. En modo organize conserva source_id,
título y orden conceptual de las lecciones actuales siempre que sea posible; no inventes source_id.
""".strip()
        try:
            return GeneratedModuleSuggestion.model_validate(await self._complete(prompt))
        except (ValidationError, TypeError, KeyError, ValueError) as error:
            raise AIProviderUnavailableError from error

    async def suggest_lesson(self, request: LessonSuggestionRequest, context: str) -> GeneratedLessonSuggestion:
        current_text = _sanitize_text(tiptap_to_text(request.content.model_dump()))
        prompt = f"""
Diseña una lección educativa editable en un CMS Tiptap.
Modo: {request.mode}. Tema: {_sanitize_text(request.topic)}.
Título actual: {_sanitize_text(request.title)}. Descripción actual: {_sanitize_text(request.description)}.
Objetivo indicado: {_sanitize_text(request.objective)}. Módulo: {_sanitize_text(request.module_title)}.
Audiencia: {_sanitize_text(request.audience)}. Nivel: {_sanitize_text(request.level)}.
Duración objetivo: {request.estimated_minutes} minutos.
Contenido actual: {current_text[:18_000]}.
Contexto adicional: {_sanitize_text(context[:18_000])}.

Devuelve solo un JSON con title, description, estimated_minutes, instructional_plan y blocks.
Los blocks solo pueden usar heading, paragraph, bullet_list, ordered_list, blockquote, code_block o horizontal_rule.
No incluyas HTML, URLs, imágenes, videos, atributos Tiptap ni identificadores personales.
""".strip()
        try:
            return GeneratedLessonSuggestion.model_validate(await self._complete(prompt))
        except (ValidationError, TypeError, KeyError, ValueError) as error:
            raise AIProviderUnavailableError from error


def get_content_suggestion_provider() -> ContentSuggestionProvider:
    if ai_config["CONTENT_PROVIDER"] == "deepseek":
        return DeepSeekContentSuggestionProvider()
    raise AIProviderUnavailableError
