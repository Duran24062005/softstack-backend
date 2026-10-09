from typing import Literal

from fastapi import APIRouter, Depends

from app.core.exception import NotFoundError
from app.middlewares.role_middleware import require_roles
from app.repositories.content_repository import LessonRepository, ModuleRepository
from app.repositories.content_revision_repository import ContentRevisionRepository
from app.routes.content_dependencies import (
    get_content_media_repository,
    get_content_revision_repository,
    get_lesson_repository,
    get_module_repository,
)
from app.routes.dependencies import get_content_blob_storage
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
from app.services.content_suggestion_provider import get_content_suggestion_provider
from app.services.content_suggestion_service import (
    apply_lesson_suggestion,
    apply_module_suggestion,
    discard_revision,
    generate_lesson_suggestion,
    generate_module_suggestion,
    get_pending_revision,
    publish_revision,
)


router = APIRouter(tags=["content suggestions"])
educator = require_roles("admin", "trainer")


@router.post("/educator/content-suggestions/modules", response_model=ContentSuggestionResponse)
async def suggest_module(
    payload: ModuleSuggestionRequest,
    _: dict = Depends(educator),
    modules: ModuleRepository = Depends(get_module_repository),
    lessons: LessonRepository = Depends(get_lesson_repository),
):
    return await generate_module_suggestion(modules, lessons, payload, get_content_suggestion_provider())


@router.post("/educator/content-suggestions/lessons", response_model=ContentSuggestionResponse)
async def suggest_lesson(
    payload: LessonSuggestionRequest,
    _: dict = Depends(educator),
    modules: ModuleRepository = Depends(get_module_repository),
    lessons: LessonRepository = Depends(get_lesson_repository),
):
    return await generate_lesson_suggestion(modules, lessons, payload, get_content_suggestion_provider())


@router.post("/educator/content-suggestions/modules/{module_id}/apply", response_model=ContentApplyResponse)
async def apply_module(
    module_id: str,
    payload: ModuleApplyRequest,
    user=Depends(educator),
    modules: ModuleRepository = Depends(get_module_repository),
    lessons: LessonRepository = Depends(get_lesson_repository),
    revisions: ContentRevisionRepository = Depends(get_content_revision_repository),
):
    return await apply_module_suggestion(modules, lessons, revisions, module_id, payload, user)


@router.post("/educator/content-suggestions/lessons/{lesson_id}/apply", response_model=ContentApplyResponse)
async def apply_lesson(
    lesson_id: str,
    payload: LessonApplyRequest,
    user=Depends(educator),
    lessons: LessonRepository = Depends(get_lesson_repository),
    revisions: ContentRevisionRepository = Depends(get_content_revision_repository),
    media_repository=Depends(get_content_media_repository),
    storage: VercelBlobStorage = Depends(get_content_blob_storage),
):
    return await apply_lesson_suggestion(lessons, revisions, lesson_id, payload, user, media_repository, storage)


@router.get("/educator/content-revisions/{target_type}/{target_id}", response_model=ContentRevisionResponse)
def pending_revision(
    target_type: Literal["module", "lesson"],
    target_id: str,
    _: dict = Depends(educator),
    revisions: ContentRevisionRepository = Depends(get_content_revision_repository),
):
    revision = get_pending_revision(revisions, target_type, target_id)
    if not revision:
        raise NotFoundError
    return revision


@router.post("/educator/content-revisions/{revision_id}/publish", response_model=ContentApplyResponse)
async def publish(
    revision_id: str,
    user=Depends(educator),
    revisions: ContentRevisionRepository = Depends(get_content_revision_repository),
    modules: ModuleRepository = Depends(get_module_repository),
    lessons: LessonRepository = Depends(get_lesson_repository),
    media_repository=Depends(get_content_media_repository),
    storage: VercelBlobStorage = Depends(get_content_blob_storage),
):
    return await publish_revision(revisions, modules, lessons, revision_id, user, media_repository, storage)


@router.delete("/educator/content-revisions/{revision_id}", response_model=ContentRevisionResponse)
def discard(
    revision_id: str,
    _: dict = Depends(educator),
    revisions: ContentRevisionRepository = Depends(get_content_revision_repository),
):
    return discard_revision(revisions, revision_id)
