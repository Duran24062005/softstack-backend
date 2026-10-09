from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId

from app.core.exception import ContentRevisionConflictError, NotFoundError
from app.models.content import ContentStatus, public_lesson, public_module
from app.repositories.content_repository import LessonRepository, ModuleRepository
from app.repositories.content_revision_repository import ContentRevisionRepository
from app.schemas.content_suggestions import (
    ContentApplyResponse,
    ContentRevisionResponse,
    ContentSuggestionResponse,
    LessonApplyRequest,
    LessonSuggestionRequest,
    ModuleApplyRequest,
    ModuleSuggestionRequest,
)
from app.services.blob_storage import VercelBlobStorage
from app.services.content_media_service import collect_document_media
from app.services.content_service import _delete_unreferenced, parse_object_id, slugify, user_object_id
from app.services.content_suggestion_provider import ContentSuggestionProvider, blocks_to_tiptap, get_content_suggestion_provider
from app.services.content_text import tiptap_to_text


PLAN_FIELD_BY_SECTION = {
    "objectives": "learning_objectives",
    "concept_map": "concept_map",
    "formats": "recommended_formats",
    "session_plan": "session_plan",
    "lesson_sequence": "lesson_sequence",
}


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _matches_base(document: dict[str, Any], base_updated_at: datetime) -> bool:
    current = _utc(document.get("updated_at"))
    expected = _utc(base_updated_at)
    return current is not None and expected is not None and current == expected


def _plan_payload(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    return value.model_dump() if hasattr(value, "model_dump") else value


def _merge_plan(current: dict[str, Any] | None, incoming: dict[str, Any], sections: Iterable[str]) -> dict[str, Any]:
    existing = current or {}
    result = {
        "central_topic": existing.get("central_topic", incoming["central_topic"]),
        "learning_objectives": existing.get("learning_objectives", incoming["learning_objectives"]),
        "concept_map": existing.get("concept_map", incoming.get("concept_map")),
        "ordering_strategy": existing.get("ordering_strategy", incoming["ordering_strategy"]),
        "ordering_rationale": existing.get("ordering_rationale", incoming["ordering_rationale"]),
        "recommended_formats": existing.get("recommended_formats", incoming["recommended_formats"]),
        "session_plan": existing.get("session_plan", incoming["session_plan"]),
        "lesson_sequence": existing.get("lesson_sequence", incoming.get("lesson_sequence", [])),
    }
    for section in sections:
        field = PLAN_FIELD_BY_SECTION.get(section)
        if field and field in incoming:
            result[field] = incoming[field]
    return result


def _module_context(module: dict[str, Any], lessons: list[dict[str, Any]]) -> str:
    return json.dumps(
        {
            "module": {
                "title": module.get("title", ""),
                "description": module.get("description", ""),
                "instructional_plan": module.get("instructional_plan"),
            },
            "lessons": [
                {
                    "id": str(lesson["_id"]),
                    "title": lesson.get("title", ""),
                    "description": lesson.get("description", ""),
                    "order": lesson.get("order", 0),
                    "instructional_plan": lesson.get("instructional_plan"),
                }
                for lesson in lessons
            ],
        },
        ensure_ascii=False,
        default=str,
    )


async def generate_module_suggestion(
    modules: ModuleRepository,
    lessons: LessonRepository,
    request: ModuleSuggestionRequest,
    provider: ContentSuggestionProvider | None = None,
) -> ContentSuggestionResponse:
    current = None
    target_id = request.module_id
    if request.mode == "organize":
        if not request.module_id:
            raise NotFoundError
        current = modules.find_by_id(parse_object_id(request.module_id))
        if not current:
            raise NotFoundError
        target_id = str(current["_id"])
        request = request.model_copy(
            update={
                "topic": request.topic or current.get("title", ""),
                "title": request.title or current.get("title", ""),
                "description": request.description or current.get("description", ""),
                "lessons": request.lessons or [
                    {
                        "id": str(lesson["_id"]),
                        "title": lesson.get("title", ""),
                        "description": lesson.get("description", ""),
                        "order": lesson.get("order", 0),
                        "estimated_minutes": lesson.get("estimated_minutes", 10),
                        "instructional_plan": lesson.get("instructional_plan"),
                    }
                    for lesson in lessons.list(current["_id"])
                ],
            }
        )
        context = _module_context(current, lessons.list(current["_id"]))
    else:
        context = "No existe contenido previo; crea una estructura nueva y coherente."
    provider = provider or get_content_suggestion_provider()
    generated = await provider.suggest_module(request, context)
    return ContentSuggestionResponse(
        target_type="module",
        mode=request.mode,
        target_id=target_id,
        base_updated_at=current.get("updated_at") if current else None,
        provider=getattr(provider, "provider_name", "unknown"),
        model=getattr(provider, "model_name", None),
        title=generated.title,
        description=generated.description,
        instructional_plan=generated.instructional_plan,
    )


async def generate_lesson_suggestion(
    modules: ModuleRepository,
    lessons: LessonRepository,
    request: LessonSuggestionRequest,
    provider: ContentSuggestionProvider | None = None,
) -> ContentSuggestionResponse:
    current = None
    target_id = request.lesson_id
    context = "No existe contenido previo; crea una lección nueva y coherente."
    if request.mode == "organize":
        if not request.lesson_id:
            raise NotFoundError
        current = lessons.find_by_id(parse_object_id(request.lesson_id))
        if not current:
            raise NotFoundError
        module = modules.find_by_id(current["module_id"])
        request = request.model_copy(
            update={
                "topic": request.topic or current.get("title", ""),
                "title": request.title or current.get("title", ""),
                "description": request.description or current.get("description", ""),
                "estimated_minutes": request.estimated_minutes or current.get("estimated_minutes", 20),
                "content": current.get("content", {"type": "doc", "content": []}),
                "module_title": request.module_title or (module or {}).get("title", ""),
                "module_description": request.module_description or (module or {}).get("description", ""),
            }
        )
        context = json.dumps(
            {
                "module": {"title": request.module_title, "description": request.module_description},
                "lesson": {"instructional_plan": current.get("instructional_plan")},
            },
            ensure_ascii=False,
            default=str,
        )
        target_id = str(current["_id"])
    provider = provider or get_content_suggestion_provider()
    generated = await provider.suggest_lesson(request, context)
    return ContentSuggestionResponse(
        target_type="lesson",
        mode=request.mode,
        target_id=target_id,
        base_updated_at=current.get("updated_at") if current else None,
        provider=getattr(provider, "provider_name", "unknown"),
        model=getattr(provider, "model_name", None),
        title=generated.title,
        description=generated.description,
        estimated_minutes=generated.estimated_minutes,
        instructional_plan=generated.instructional_plan,
        content=blocks_to_tiptap(generated.blocks),
    )


def _revision_response(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "target_type": document["target_type"],
        "target_id": str(document["target_id"]),
        "status": document.get("status", "pending"),
        "source": document.get("source", "ai_content_suggestion"),
        "base_updated_at": document["base_updated_at"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }


def _revision_or_update(
    revisions: ContentRevisionRepository,
    *,
    target_type: str,
    target_id: ObjectId,
    base_updated_at: datetime,
    changes: dict[str, Any],
    lesson_orders: list[dict[str, Any]],
    user: dict[str, Any],
) -> dict[str, Any]:
    document = revisions.find_pending(target_type, target_id)
    payload = {
        "target_type": target_type,
        "target_id": target_id,
        "source": "ai_content_suggestion",
        "base_updated_at": base_updated_at,
        "changes": changes,
        "lesson_orders": lesson_orders,
        "created_by": user_object_id(user),
    }
    return revisions.update(document["_id"], payload) if document else revisions.create(payload)


async def apply_module_suggestion(
    modules: ModuleRepository,
    lessons: LessonRepository,
    revisions: ContentRevisionRepository,
    module_id: str,
    request: ModuleApplyRequest,
    user: dict[str, Any],
) -> dict[str, Any]:
    parsed = parse_object_id(module_id)
    current = modules.find_by_id(parsed)
    if not current:
        raise NotFoundError
    if not _matches_base(current, request.base_updated_at):
        raise ContentRevisionConflictError
    incoming_plan = request.instructional_plan.model_dump()
    merged_plan = _merge_plan(current.get("instructional_plan"), incoming_plan, request.plan_sections)
    lesson_orders = [{"lesson_id": parse_object_id(item.lesson_id), "order": item.order} for item in request.lesson_orders]
    for item in lesson_orders:
        lesson = lessons.find_by_id(item["lesson_id"])
        if not lesson or lesson.get("module_id") != parsed:
            raise NotFoundError
    changes = {"instructional_plan": merged_plan}
    if "fields" in request.plan_sections:
        changes.update({"title": request.title.strip(), "description": request.description.strip(), "slug": slugify(request.title)})
    if current.get("status") == ContentStatus.PUBLISHED.value:
        revision = _revision_or_update(revisions, target_type="module", target_id=parsed, base_updated_at=request.base_updated_at, changes=changes, lesson_orders=lesson_orders, user=user)
        return ContentApplyResponse(outcome="revision_created", revision=_revision_response(revision)).model_dump()
    updated = modules.update(parsed, changes)
    for item in lesson_orders:
        lessons.update(item["lesson_id"], {"order": item["order"]})
    return ContentApplyResponse(outcome="updated", module=public_module(updated or current)).model_dump()


async def apply_lesson_suggestion(
    lessons: LessonRepository,
    revisions: ContentRevisionRepository,
    lesson_id: str,
    request: LessonApplyRequest,
    user: dict[str, Any],
    media_repository=None,
    storage: VercelBlobStorage | None = None,
) -> dict[str, Any]:
    parsed = parse_object_id(lesson_id)
    current = lessons.find_by_id(parsed)
    if not current:
        raise NotFoundError
    if not _matches_base(current, request.base_updated_at):
        raise ContentRevisionConflictError
    plan_sections = [section for section in request.sections if section in PLAN_FIELD_BY_SECTION]
    merged_plan = _merge_plan(current.get("instructional_plan"), request.instructional_plan.model_dump(), plan_sections)
    changes: dict[str, Any] = {"instructional_plan": merged_plan}
    if "fields" in request.sections:
        changes.update({"title": request.title.strip(), "description": request.description.strip(), "estimated_minutes": request.estimated_minutes})
    if "content" in request.sections and request.content is not None:
        changes["content"] = request.content.model_dump()
    if current.get("status") == ContentStatus.PUBLISHED.value:
        revision = _revision_or_update(revisions, target_type="lesson", target_id=parsed, base_updated_at=request.base_updated_at, changes=changes, lesson_orders=[], user=user)
        return ContentApplyResponse(outcome="revision_created", revision=_revision_response(revision)).model_dump()
    if "content" in changes:
        old_assets = current.get("media_assets", [])
        changes["media_assets"] = collect_document_media(changes["content"])
        updated = lessons.update(parsed, changes)
        if media_repository is not None and storage is not None:
            await _delete_unreferenced(storage, media_repository, [asset for asset in old_assets if asset not in changes["media_assets"]])
    else:
        updated = lessons.update(parsed, changes)
    return ContentApplyResponse(outcome="updated", lesson=public_lesson(updated or current)).model_dump()


def get_pending_revision(revisions: ContentRevisionRepository, target_type: str, target_id: str) -> dict[str, Any] | None:
    revision = revisions.find_pending(target_type, parse_object_id(target_id))
    return _revision_response(revision) if revision else None


async def publish_revision(
    revisions: ContentRevisionRepository,
    modules: ModuleRepository,
    lessons: LessonRepository,
    revision_id: str,
    user: dict[str, Any],
    media_repository=None,
    storage: VercelBlobStorage | None = None,
) -> dict[str, Any]:
    revision = revisions.find_by_id(parse_object_id(revision_id))
    if not revision or revision.get("status") != "pending":
        raise NotFoundError
    target_id = revision["target_id"]
    changes = revision.get("changes", {})
    if revision["target_type"] == "module":
        current = modules.find_by_id(target_id)
        if not current or not _matches_base(current, revision["base_updated_at"]):
            raise ContentRevisionConflictError
        updated = modules.update(target_id, changes)
        for item in revision.get("lesson_orders", []):
            lessons.update(item["lesson_id"], {"order": item["order"]})
        revisions.mark(revision["_id"], "published")
        return ContentApplyResponse(outcome="updated", module=public_module(updated or current)).model_dump()
    current = lessons.find_by_id(target_id)
    if not current or not _matches_base(current, revision["base_updated_at"]):
        raise ContentRevisionConflictError
    lesson_changes = dict(changes)
    if "content" in lesson_changes:
        old_assets = current.get("media_assets", [])
        lesson_changes["media_assets"] = collect_document_media(lesson_changes["content"])
    updated = lessons.update(target_id, lesson_changes)
    if "content" in lesson_changes and media_repository is not None and storage is not None:
        await _delete_unreferenced(storage, media_repository, [asset for asset in old_assets if asset not in lesson_changes["media_assets"]])
    revisions.mark(revision["_id"], "published")
    return ContentApplyResponse(outcome="updated", lesson=public_lesson(updated or current)).model_dump()


def discard_revision(revisions: ContentRevisionRepository, revision_id: str) -> dict[str, Any]:
    revision = revisions.find_by_id(parse_object_id(revision_id))
    if not revision or revision.get("status") != "pending":
        raise NotFoundError
    revisions.delete(revision["_id"])
    return _revision_response({**revision, "status": "discarded", "updated_at": datetime.now(timezone.utc)})
