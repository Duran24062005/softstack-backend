from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vercel.blob import AsyncBlobClient, BlobNotFoundError, list_objects_async

from app.config.config import blob_config
from app.core.exception import BlobStorageOperationError, BlobStorageUnavailableError, ContentMediaUnavailableError


@dataclass(frozen=True)
class StoredBlob:
    pathname: str
    content_type: str
    size: int
    etag: str
    url: str


class VercelBlobStorage:
    """Application boundary around the Vercel Blob Python SDK."""

    def __init__(self, client: AsyncBlobClient | None = None, config: dict[str, Any] | None = None):
        self.config = config or blob_config
        if client is not None:
            self.client = client
            return
        if not self.config["STORE_ID"] or not self.config["READ_WRITE_TOKEN"]:
            if self.config.get("ACCESS") == "public":
                raise ContentMediaUnavailableError
            raise BlobStorageUnavailableError
        self.client = AsyncBlobClient(token=self.config["READ_WRITE_TOKEN"])

    async def upload(self, pathname: str, body: bytes, content_type: str) -> StoredBlob:
        try:
            result = await self.client.put(
                pathname,
                body,
                access=self.config.get("ACCESS", "private"),
                content_type=content_type,
                add_random_suffix=False,
            )
        except Exception as error:
            raise BlobStorageOperationError from error
        return StoredBlob(
            pathname=result.pathname,
            content_type=result.content_type,
            size=len(body),
            # PutBlobResult from the Python SDK does not expose an ETag.
            # Keep the metadata field stable for the application contract.
            etag=getattr(result, "etag", ""),
            url=result.url,
        )

    async def get(self, pathname: str) -> Any:
        try:
            result = await self.client.get(pathname, access=self.config.get("ACCESS", "private"))
        except BlobNotFoundError as error:
            raise FileNotFoundError(pathname) from error
        except Exception as error:
            raise BlobStorageOperationError from error
        if result is None:
            raise FileNotFoundError(pathname)
        return result

    async def delete(self, pathname: str) -> None:
        try:
            await self.client.delete(pathname)
        except Exception as error:
            raise BlobStorageOperationError from error

    async def list(self, prefix: str) -> list[Any]:
        try:
            result = await list_objects_async(prefix=prefix, token=self.config["READ_WRITE_TOKEN"])
        except Exception as error:
            raise BlobStorageOperationError from error
        if isinstance(result, dict):
            return result.get("blobs", [])
        return list(getattr(result, "blobs", result or []))
