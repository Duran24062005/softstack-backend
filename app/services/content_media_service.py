from __future__ import annotations

import asyncio
import ipaddress
import logging
import mimetypes
import socket
from datetime import datetime, timedelta, timezone
from pathlib import PurePosixPath
from typing import Any
from urllib.error import URLError
from urllib.parse import unquote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from app.config.config import content_blob_config
from app.core.exception import ContentMediaInvalidError, ContentMediaOperationError
from app.repositories.content_media_repository import ContentMediaRepository
from app.schemas.content_media import MediaReference
from app.services.blob_storage import StoredBlob, VercelBlobStorage

logger = logging.getLogger(__name__)


def _allowed_types() -> set[str]:
    return content_blob_config["ALLOWED_IMAGE_CONTENT_TYPES"] | content_blob_config["ALLOWED_VIDEO_CONTENT_TYPES"]


def _max_size(content_type: str) -> int:
    if content_type.startswith("image/"):
        return content_blob_config["MAX_IMAGE_SIZE_BYTES"]
    if content_type.startswith("video/"):
        return content_blob_config["MAX_VIDEO_SIZE_BYTES"]
    raise ContentMediaInvalidError


def _expected_kind(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "image"
    if content_type.startswith("video/"):
        return "video"
    raise ContentMediaInvalidError


def _validate_pathname(pathname: str) -> str:
    if not pathname.startswith(content_blob_config["PREFIX"]):
        raise ContentMediaInvalidError
    if "\\" in pathname or any(part in {"", ".", ".."} for part in pathname.split("/")):
        raise ContentMediaInvalidError
    return pathname


def _validate_blob_url(url: str, pathname: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or not parsed.hostname:
        raise ContentMediaInvalidError
    configured_host = content_blob_config.get("PUBLIC_HOST", "")
    if not configured_host or parsed.hostname.lower() != configured_host.lower():
        raise ContentMediaInvalidError
    if unquote(parsed.path).lstrip("/") != pathname:
        raise ContentMediaInvalidError


def validate_media_reference(reference: MediaReference | dict[str, Any], expected_kind: str | None = None) -> dict[str, Any]:
    raw = reference.model_dump() if isinstance(reference, MediaReference) else reference
    try:
        url = str(raw["url"])
        pathname = _validate_pathname(str(raw["pathname"]))
        content_type = str(raw["content_type"]).lower().split(";", 1)[0].strip()
        size = int(raw["size"])
    except (KeyError, TypeError, ValueError) as error:
        raise ContentMediaInvalidError from error
    if content_type not in _allowed_types() or size < 1 or size > _max_size(content_type):
        raise ContentMediaInvalidError
    if expected_kind and _expected_kind(content_type) != expected_kind:
        raise ContentMediaInvalidError
    _validate_blob_url(url, pathname)
    return {"url": url, "pathname": pathname, "content_type": content_type, "size": size}


def collect_document_media(document: dict[str, Any]) -> list[dict[str, Any]]:
    collected: dict[str, dict[str, Any]] = {}

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        node_type = value.get("type")
        if node_type in {"image", "video"}:
            attrs = value.get("attrs") or {}
            reference = {
                "url": attrs.get("src"),
                "pathname": attrs.get("mediaPathname"),
                "content_type": attrs.get("mediaContentType"),
                "size": attrs.get("mediaSize"),
            }
            normalized = validate_media_reference(reference, "image" if node_type == "image" else "video")
            collected[normalized["pathname"]] = normalized
        for child in value.values():
            visit(child)

    visit(document)
    return list(collected.values())


def validate_cover_media(reference: MediaReference | dict[str, Any] | None) -> dict[str, Any] | None:
    if reference is None:
        return None
    return validate_media_reference(reference)


def _signature_matches(content_type: str, body: bytes) -> bool:
    if content_type == "image/jpeg":
        return body.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return body.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP"
    if content_type == "image/avif":
        return len(body) >= 12 and body[4:8] == b"ftyp" and body[8:12] in {b"avif", b"avis"}
    if content_type in {"video/mp4", "video/quicktime"}:
        return len(body) >= 12 and body[4:8] == b"ftyp"
    if content_type == "video/webm":
        return body.startswith(b"\x1a\x45\xdf\xa3")
    return False


def _assert_safe_external_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password or not parsed.hostname:
        raise ContentMediaInvalidError
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise ContentMediaInvalidError from error
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise ContentMediaInvalidError


class _SafeRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        _assert_safe_external_url(new_url)
        return super().redirect_request(request, file, code, message, headers, new_url)


def _download_external(url: str, kind: str | None) -> tuple[bytes, str]:
    _assert_safe_external_url(url)
    request = Request(url, headers={"User-Agent": "SoftStack-content-media/1.0"})
    try:
        with build_opener(_SafeRedirectHandler()).open(request, timeout=content_blob_config["IMPORT_TIMEOUT_SECONDS"]) as response:
            final_url = response.geturl()
            _assert_safe_external_url(final_url)
            content_type = (response.headers.get_content_type() or mimetypes.guess_type(final_url)[0] or "").lower()
            if content_type not in _allowed_types() or (kind and _expected_kind(content_type) != kind):
                raise ContentMediaInvalidError
            limit = _max_size(content_type)
            declared_size = response.headers.get("Content-Length")
            if declared_size and int(declared_size) > limit:
                raise ContentMediaInvalidError
            body = response.read(limit + 1)
    except ContentMediaInvalidError:
        raise
    except (OSError, URLError, ValueError) as error:
        raise ContentMediaOperationError from error
    if not body or len(body) > _max_size(content_type) or not _signature_matches(content_type, body):
        raise ContentMediaInvalidError
    return body, content_type


def _extension(content_type: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/avif": "avif",
        "video/mp4": "mp4",
        "video/webm": "webm",
        "video/quicktime": "mov",
    }[content_type]


def stored_blob_reference(blob: StoredBlob) -> dict[str, Any]:
    return {
        "url": blob.url,
        "pathname": blob.pathname,
        "content_type": blob.content_type,
        "size": blob.size,
    }


async def import_external_url(storage: VercelBlobStorage, source_url: str, kind: str | None = None) -> dict[str, Any]:
    body, content_type = await asyncio.to_thread(_download_external, source_url, kind)
    pathname = str(PurePosixPath(content_blob_config["PREFIX"]) / f"{uuid4()}.{_extension(content_type)}")
    blob = await storage.upload(pathname, body, content_type)
    return stored_blob_reference(blob)


async def delete_content_media(storage: VercelBlobStorage, pathname: str) -> None:
    _validate_pathname(pathname)
    await storage.delete(pathname)


async def cleanup_orphaned_media(storage: VercelBlobStorage, repository: ContentMediaRepository) -> int:
    referenced = repository.referenced_pathnames()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=content_blob_config["ORPHAN_RETENTION_HOURS"])
    deleted = 0
    for blob in await storage.list(content_blob_config["PREFIX"]):
        if isinstance(blob, dict):
            pathname = blob.get("pathname")
            uploaded_at = blob.get("uploadedAt") or blob.get("uploaded_at")
        else:
            pathname = getattr(blob, "pathname", None)
            uploaded_at = getattr(blob, "uploaded_at", None) or getattr(blob, "uploadedAt", None)
        if not pathname or pathname in referenced or not uploaded_at:
            continue
        if isinstance(uploaded_at, str):
            uploaded_at = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00"))
        if uploaded_at.tzinfo is None:
            uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
        if uploaded_at < cutoff:
            try:
                await storage.delete(pathname)
                deleted += 1
            except Exception:
                logger.warning("Could not delete orphaned content media", extra={"pathname": pathname}, exc_info=True)
    return deleted
