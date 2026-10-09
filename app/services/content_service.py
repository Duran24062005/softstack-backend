import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.exception import ConflictError, NotFoundError
from app.models.content import ContentStatus, public_lesson, public_module
from app.repositories.content_media_repository import ContentMediaRepository
from app.repositories.content_repository import LessonRepository, ModuleRepository, ProgressRepository
from app.services.blob_storage import VercelBlobStorage
from app.services.content_media_service import collect_document_media, delete_content_media, validate_cover_media

logger = logging.getLogger(__name__)


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


async def _delete_unreferenced(storage: VercelBlobStorage, media_repository: ContentMediaRepository, assets: list[dict[str, Any]]) -> None:
    for asset in assets:
        pathname = asset.get("pathname")
        if not pathname or media_repository.is_referenced(pathname):
            continue
        try:
            await delete_content_media(storage, pathname)
        except Exception:
            logger.warning("Could not delete content media", extra={"pathname": pathname}, exc_info=True)


async def create_module(modules: ModuleRepository, media_repository: ContentMediaRepository, storage: VercelBlobStorage, payload, user: dict[str, Any]) -> dict[str, Any]:
    cover_media = validate_cover_media(payload.cover_media)
    media_assets = [cover_media] if cover_media else []
    now = datetime.now(timezone.utc)
    instructional_plan = getattr(payload, "instructional_plan", None)
    document = {
        "title": payload.title.strip(),
        "slug": slugify(payload.title),
        "description": payload.description.strip(),
        "order": payload.order,
        "status": payload.status.value,
        "cover_media": cover_media,
        "instructional_plan": instructional_plan.model_dump() if instructional_plan else None,
        "media_assets": media_assets,
        "created_by": user_object_id(user),
        "created_at": now,
        "updated_at": now,
    }
    try:
        return public_module(modules.create(document))
    except DuplicateKeyError as error:
        await _delete_unreferenced(storage, media_repository, media_assets)
        raise ConflictError from error
    except Exception:
        await _delete_unreferenced(storage, media_repository, media_assets)
        raise


async def update_module(modules: ModuleRepository, media_repository: ContentMediaRepository, storage: VercelBlobStorage, module_id: str, payload) -> dict[str, Any]:
    parsed = parse_object_id(module_id)
    current = modules.find_by_id(parsed)
    if not current:
        raise NotFoundError
    changes = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None or key == "cover_media"
    }
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        changes["slug"] = slugify(changes["title"])
    if "status" in changes:
        changes["status"] = changes["status"].value
    old_assets = current.get("media_assets", [])
    new_assets = old_assets
    if "cover_media" in changes:
        changes["cover_media"] = validate_cover_media(payload.cover_media)
        new_assets = [changes["cover_media"]] if changes["cover_media"] else []
        changes["media_assets"] = new_assets
    try:
        updated = modules.update(parsed, changes)
        if not updated:
            raise NotFoundError
    except DuplicateKeyError as error:
        await _delete_unreferenced(storage, media_repository, [asset for asset in new_assets if asset not in old_assets])
        raise ConflictError from error
    except Exception:
        await _delete_unreferenced(storage, media_repository, [asset for asset in new_assets if asset not in old_assets])
        raise
    if "cover_media" in changes:
        await _delete_unreferenced(storage, media_repository, [asset for asset in old_assets if asset not in new_assets])
    return public_module(updated)


async def create_lesson(modules: ModuleRepository, lessons: LessonRepository, media_repository: ContentMediaRepository, storage: VercelBlobStorage, module_id: str, payload, user: dict[str, Any]) -> dict[str, Any]:
    parsed_module = parse_object_id(module_id)
    if not modules.find_by_id(parsed_module):
        raise NotFoundError
    content = payload.content.model_dump()
    media_assets = collect_document_media(content)
    now = datetime.now(timezone.utc)
    current_id = user_object_id(user)
    instructional_plan = getattr(payload, "instructional_plan", None)
    document = {
        "module_id": parsed_module,
        "title": payload.title.strip(),
        "slug": slugify(payload.title),
        "description": payload.description.strip(),
        "content": content,
        "instructional_plan": instructional_plan.model_dump() if instructional_plan else None,
        "media_assets": media_assets,
        "order": payload.order,
        "status": payload.status.value,
        "estimated_minutes": payload.estimated_minutes,
        "created_by": current_id,
        "updated_by": current_id,
        "created_at": now,
        "updated_at": now,
    }
    try:
        return public_lesson(lessons.create(document))
    except DuplicateKeyError as error:
        await _delete_unreferenced(storage, media_repository, media_assets)
        raise ConflictError from error
    except Exception:
        await _delete_unreferenced(storage, media_repository, media_assets)
        raise


async def update_lesson(lessons: LessonRepository, media_repository: ContentMediaRepository, storage: VercelBlobStorage, lesson_id: str, payload, user: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_object_id(lesson_id)
    current = lessons.find_by_id(parsed)
    if not current:
        raise NotFoundError
    changes = {
        key: value
        for key, value in payload.model_dump(exclude_unset=True).items()
        if value is not None
    }
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        changes["slug"] = slugify(changes["title"])
    old_assets = current.get("media_assets", [])
    new_assets = old_assets
    if "content" in changes:
        changes["media_assets"] = collect_document_media(changes["content"])
        new_assets = changes["media_assets"]
    if "status" in changes:
        changes["status"] = changes["status"].value
    changes["updated_by"] = user_object_id(user)
    try:
        updated = lessons.update(parsed, changes)
        if not updated:
            raise NotFoundError
    except DuplicateKeyError as error:
        await _delete_unreferenced(storage, media_repository, [asset for asset in new_assets if asset not in old_assets])
        raise ConflictError from error
    except Exception:
        await _delete_unreferenced(storage, media_repository, [asset for asset in new_assets if asset not in old_assets])
        raise
    if "content" in changes:
        await _delete_unreferenced(storage, media_repository, [asset for asset in old_assets if asset not in new_assets])
    return public_lesson(updated)


def get_progress(progress: ProgressRepository, lessons: LessonRepository, user: dict[str, Any]) -> dict[str, Any]:
    completed = progress.completed_for_user(user_object_id(user))
    published_lessons = lessons.list(status=ContentStatus.PUBLISHED.value)
    total = len(published_lessons)
    ids = [str(item["lesson_id"]) for item in completed]
    try:
        completed_modules = list(progress.completed_modules_for_user(user_object_id(user)))
    except (AttributeError, TypeError):
        completed_modules = []
    module_ids = [str(item["module_id"]) for item in completed_modules]
    total_modules = len({str(lesson["module_id"]) for lesson in published_lessons if lesson.get("module_id")})
    return {
        "completed_lesson_ids": ids,
        "completed_count": len(ids),
        "total_lessons": total,
        "percentage": round((len(ids) / total) * 100, 1) if total else 0,
        "completed_module_ids": module_ids,
        "completed_module_count": len(module_ids),
        "total_modules": total_modules,
        "module_percentage": round((len(module_ids) / total_modules) * 100, 1) if total_modules else 0,
    }


def complete_lesson(lessons: LessonRepository, progress: ProgressRepository, lesson_id: str, user: dict[str, Any]) -> dict[str, Any]:
    lesson = lessons.find_by_id(parse_object_id(lesson_id))
    if not lesson or lesson.get("status") != ContentStatus.PUBLISHED.value:
        raise NotFoundError
    progress.complete(user_object_id(user), lesson["_id"], lesson["module_id"])
    return get_progress(progress, lessons, user)
