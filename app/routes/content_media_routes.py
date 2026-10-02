from __future__ import annotations

import hmac

from fastapi import APIRouter, Depends, Request, status

from app.config.config import cron_config
from app.core.exception import ConflictError, InvalidTokenError
from app.middlewares.role_middleware import require_roles
from app.repositories.content_media_repository import ContentMediaRepository
from app.routes.content_dependencies import get_content_media_repository
from app.routes.dependencies import get_content_blob_storage
from app.schemas.content_media import ContentMediaDeleteRequest, ContentMediaImportRequest, MediaReference
from app.services.blob_storage import VercelBlobStorage
from app.services.content_media_service import cleanup_orphaned_media, delete_content_media, import_external_url

router = APIRouter(tags=["content-media"])
admin = require_roles("admin")


@router.post("/admin/content-media/import", response_model=MediaReference, status_code=status.HTTP_201_CREATED)
async def import_media(payload: ContentMediaImportRequest, _: dict = Depends(admin), storage: VercelBlobStorage = Depends(get_content_blob_storage)):
    return await import_external_url(storage, payload.source_url, payload.kind)


@router.delete("/admin/content-media", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(payload: ContentMediaDeleteRequest, _: dict = Depends(admin), repository: ContentMediaRepository = Depends(get_content_media_repository), storage: VercelBlobStorage = Depends(get_content_blob_storage)):
    if repository.is_referenced(payload.pathname):
        raise ConflictError
    await delete_content_media(storage, payload.pathname)
    return None


@router.api_route("/internal/content-media/cleanup", methods=["GET", "POST"])
async def cleanup_media(request: Request, repository: ContentMediaRepository = Depends(get_content_media_repository), storage: VercelBlobStorage = Depends(get_content_blob_storage)):
    authorization = request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ").strip()
    if not cron_config["SECRET"] or not hmac.compare_digest(token, cron_config["SECRET"]):
        raise InvalidTokenError
    return {"deleted": await cleanup_orphaned_media(storage, repository)}
