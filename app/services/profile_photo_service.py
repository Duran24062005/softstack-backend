from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.config.config import blob_config
from app.core.exception import InvalidProfilePhotoError, NotFoundError
from app.models.auth import public_user
from app.repositories.user_repository import UserRepository
from app.services.blob_storage import StoredBlob, VercelBlobStorage

logger = logging.getLogger(__name__)

_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _matches_signature(content_type: str, body: bytes) -> bool:
    if content_type == "image/jpeg":
        return body.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return body.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
    return False


async def _read_validated_photo(file: UploadFile) -> tuple[bytes, str, str]:
    content_type = (file.content_type or "").lower()
    if content_type not in blob_config["ALLOWED_CONTENT_TYPES"]:
        raise InvalidProfilePhotoError

    body = await file.read(blob_config["MAX_FILE_SIZE_BYTES"] + 1)
    if not body or len(body) > blob_config["MAX_FILE_SIZE_BYTES"]:
        raise InvalidProfilePhotoError
    if not _matches_signature(content_type, body):
        raise InvalidProfilePhotoError
    return body, _EXTENSIONS[content_type], content_type


def _metadata(blob: StoredBlob) -> dict[str, Any]:
    return {
        "pathname": blob.pathname,
        "content_type": blob.content_type,
        "size": blob.size,
        "etag": blob.etag,
        "uploaded_at": datetime.now(timezone.utc),
    }


class ProfilePhotoService:
    def __init__(self, users: UserRepository | None, storage: VercelBlobStorage):
        self.users = users
        self.storage = storage

    async def upload(self, user: dict[str, Any], file: UploadFile) -> dict[str, Any]:
        body, extension, content_type = await _read_validated_photo(file)
        pathname = str(PurePosixPath("profile-photos") / str(user["_id"]) / f"{uuid4()}.{extension}")
        new_blob = await self.storage.upload(pathname, body, content_type)
        old_photo = user.get("profile_photo")

        try:
            updated = self.users.update(user["_id"], {"profile_photo": _metadata(new_blob)})
            if not updated:
                raise NotFoundError
        except Exception:
            try:
                await self.storage.delete(new_blob.pathname)
            except Exception:
                logger.exception("Could not clean up profile photo after database update failure")
            raise

        if old_photo and old_photo.get("pathname"):
            try:
                await self.storage.delete(old_photo["pathname"])
            except Exception:
                logger.warning("Could not delete replaced profile photo", exc_info=True)

        return public_user(updated)

    async def delete(self, user: dict[str, Any]) -> dict[str, Any]:
        old_photo = user.get("profile_photo")
        if not old_photo:
            return public_user(user)

        updated = self.users.update(user["_id"], {"profile_photo": None})
        if not updated:
            raise NotFoundError

        if old_photo.get("pathname"):
            try:
                await self.storage.delete(old_photo["pathname"])
            except Exception:
                logger.warning("Could not delete removed profile photo", exc_info=True)

        return public_user(updated)

    async def get(self, user: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
        photo = user.get("profile_photo")
        if not photo or not photo.get("pathname"):
            raise NotFoundError
        try:
            result = await self.storage.get(photo["pathname"])
        except FileNotFoundError as error:
            raise NotFoundError from error
        return result, photo
