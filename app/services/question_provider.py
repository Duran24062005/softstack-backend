import json
import re
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.config.config import ai_config
from app.core.exception import AIProviderUnavailableError
from app.services.content_text import tiptap_to_text


class GeneratedOption(BaseModel):
    id: str = Field(min_length=1, max_length=8)
    text: str = Field(min_length=1, max_length=500)


class GeneratedQuestion(BaseModel):
    prompt: str = Field(min_length=10, max_length=1_000)
    options: list[GeneratedOption] = Field(min_length=4, max_length=4)
    correct_option_id: str
    explanation: str = Field(default="", max_length=1_000)
    competency: str = Field(default="Comprensión del tema", max_length=120)
    difficulty: Literal["basic", "intermediate", "advanced"] = "intermediate"

    @model_validator(mode="after")
    def validate_options(self):
        ids = [option.id for option in self.options]
        if len(set(ids)) != 4 or self.correct_option_id not in ids:
            raise ValueError("The generated question must have four unique options and a valid answer")
        return self


class QuestionProvider(Protocol):
    async def generate(self, *, title: str, description: str, content: str, count: int) -> list[GeneratedQuestion]: ...


def _json_content(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned


class DeepSeekQuestionProvider:
    provider_name = "deepseek"

    @property
    def model_name(self) -> str:
        return ai_config["DEEPSEEK_MODEL"]

    async def generate(self, *, title: str, description: str, content: str, count: int) -> list[GeneratedQuestion]:
        api_key = ai_config["DEEPSEEK_API_KEY"]
        if not api_key:
            raise AIProviderUnavailableError
        prompt = f"""
Genera exactamente {count} preguntas educativas de selección única sobre el siguiente contenido.
Devuelve únicamente JSON válido con esta forma: {{\"questions\":[{{\"prompt\":\"...\",\"options\":[{{\"id\":\"a\",\"text\":\"...\"}},{{\"id\":\"b\",\"text\":\"...\"}},{{\"id\":\"c\",\"text\":\"...\"}},{{\"id\":\"d\",\"text\":\"...\"}}],\"correct_option_id\":\"a\",\"explanation\":\"...\",\"competency\":\"...\",\"difficulty\":\"basic|intermediate|advanced\"}}]}}.
Cada pregunta debe evaluar comprensión o aplicación, evitar ambigüedades y tener una sola respuesta correcta.
Título: {title}
Descripción: {description}
Contenido: {content[:18_000]}
""".strip()
        payload = {
            "model": ai_config["DEEPSEEK_MODEL"],
            "messages": [
                {"role": "system", "content": "Eres un diseñador instruccional. Responde en JSON."},
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
                content_value = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(_json_content(content_value))
            questions = [GeneratedQuestion.model_validate(item) for item in parsed["questions"]]
            if len(questions) != count:
                raise ValueError("The provider returned an unexpected number of questions")
            return questions
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError, ValidationError, ValueError) as error:
            raise AIProviderUnavailableError from error


def get_question_provider() -> QuestionProvider:
    if ai_config["PROVIDER"] == "deepseek":
        return DeepSeekQuestionProvider()
    raise AIProviderUnavailableError
