import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.exception import ConflictError, NotFoundError
from app.models.content import ContentStatus, public_lesson, public_module
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository


def parse_object_id(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except Exception as error:
        raise NotFoundError from error


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def user_object_id(user: dict[str, Any]) -> ObjectId:
    return user.get("_id") or ObjectId(user["id"])


def list_modules(modules: ModuleRepository) -> list[dict[str, Any]]:
    return [public_module(module) for module in modules.list(ContentStatus.PUBLISHED.value)]


def list_admin_modules(modules: ModuleRepository) -> list[dict[str, Any]]:
    return [public_module(module) for module in modules.list()]


def get_admin_module(modules: ModuleRepository, module_id: str) -> dict[str, Any]:
    module = modules.find_by_id(parse_object_id(module_id))
    if not module:
        raise NotFoundError
    return public_module(module)


def get_module(modules: ModuleRepository, module_id: str) -> dict[str, Any]:
    module = modules.find_by_id(parse_object_id(module_id))
    if not module or module.get("status") != ContentStatus.PUBLISHED.value:
        raise NotFoundError
    return public_module(module)


def list_module_lessons(modules: ModuleRepository, lessons: LessonRepository, module_id: str) -> list[dict[str, Any]]:
    parsed = parse_object_id(module_id)
    if not modules.find_by_id(parsed):
        raise NotFoundError
    return [public_lesson(lesson) for lesson in lessons.list(parsed, ContentStatus.PUBLISHED.value)]


def list_admin_module_lessons(modules: ModuleRepository, lessons: LessonRepository, module_id: str) -> list[dict[str, Any]]:
    parsed = parse_object_id(module_id)
    if not modules.find_by_id(parsed):
        raise NotFoundError
    return [public_lesson(lesson) for lesson in lessons.list(parsed)]


def get_lesson(lessons: LessonRepository, lesson_id: str, include_drafts: bool = False) -> dict[str, Any]:
    lesson = lessons.find_by_id(parse_object_id(lesson_id))
    if not lesson or (not include_drafts and lesson.get("status") != ContentStatus.PUBLISHED.value):
        raise NotFoundError
    return public_lesson(lesson)


def create_module(modules: ModuleRepository, payload, user: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    document = {"title": payload.title.strip(), "slug": slugify(payload.title), "description": payload.description.strip(), "order": payload.order, "status": payload.status.value, "created_by": user_object_id(user), "created_at": now, "updated_at": now}
    try:
        return public_module(modules.create(document))
    except DuplicateKeyError as error:
        raise ConflictError from error


def update_module(modules: ModuleRepository, module_id: str, payload) -> dict[str, Any]:
    parsed = parse_object_id(module_id)
    if not modules.find_by_id(parsed):
        raise NotFoundError
    changes = payload.model_dump(exclude_none=True)
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        changes["slug"] = slugify(changes["title"])
    if "status" in changes:
        changes["status"] = changes["status"].value
    try:
        return public_module(modules.update(parsed, changes))
    except DuplicateKeyError as error:
        raise ConflictError from error


def create_lesson(modules: ModuleRepository, lessons: LessonRepository, module_id: str, payload, user: dict[str, Any]) -> dict[str, Any]:
    parsed_module = parse_object_id(module_id)
    if not modules.find_by_id(parsed_module):
        raise NotFoundError
    now = datetime.now(timezone.utc)
    current_id = user_object_id(user)
    document = {"module_id": parsed_module, "title": payload.title.strip(), "slug": slugify(payload.title), "description": payload.description.strip(), "content": payload.content.model_dump(), "order": payload.order, "status": payload.status.value, "estimated_minutes": payload.estimated_minutes, "created_by": current_id, "updated_by": current_id, "created_at": now, "updated_at": now}
    try:
        return public_lesson(lessons.create(document))
    except DuplicateKeyError as error:
        raise ConflictError from error


def update_lesson(lessons: LessonRepository, lesson_id: str, payload, user: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_object_id(lesson_id)
    if not lessons.find_by_id(parsed):
        raise NotFoundError
    changes = payload.model_dump(exclude_none=True)
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        changes["slug"] = slugify(changes["title"])
    if "content" in changes:
        changes["content"] = changes["content"]
    if "status" in changes:
        changes["status"] = changes["status"].value
    changes["updated_by"] = user_object_id(user)
    try:
        return public_lesson(lessons.update(parsed, changes))
    except DuplicateKeyError as error:
        raise ConflictError from error


def get_progress(progress: ProgressRepository, lessons: LessonRepository, user: dict[str, Any]) -> dict[str, Any]:
    completed = progress.completed_for_user(user_object_id(user))
    total = len(lessons.list(status=ContentStatus.PUBLISHED.value))
    ids = [str(item["lesson_id"]) for item in completed]
    return {"completed_lesson_ids": ids, "completed_count": len(ids), "total_lessons": total, "percentage": round((len(ids) / total) * 100, 1) if total else 0}


def complete_lesson(lessons: LessonRepository, progress: ProgressRepository, lesson_id: str, user: dict[str, Any]) -> dict[str, Any]:
    lesson = lessons.find_by_id(parse_object_id(lesson_id))
    if not lesson or lesson.get("status") != ContentStatus.PUBLISHED.value:
        raise NotFoundError
    progress.complete(user_object_id(user), lesson["_id"], lesson["module_id"])
    return get_progress(progress, lessons, user)
