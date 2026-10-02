from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from vercel.blob import AsyncBlobClient, BlobNotFoundError

from app.config.config import blob_config
from app.core.exception import BlobStorageOperationError, BlobStorageUnavailableError


@dataclass(frozen=True)
class StoredBlob:
    pathname: str
    content_type: str
    size: int
    etag: str
    url: str


class VercelBlobStorage:
    """Application boundary around the Vercel Blob Python SDK."""

    def __init__(self, client: AsyncBlobClient | None = None):
        if client is not None:
            self.client = client
            return
        if not blob_config["STORE_ID"] or not blob_config["READ_WRITE_TOKEN"]:
            raise BlobStorageUnavailableError
        self.client = AsyncBlobClient(token=blob_config["READ_WRITE_TOKEN"])

    async def upload(self, pathname: str, body: bytes, content_type: str) -> StoredBlob:
        try:
            result = await self.client.put(
                pathname,
                body,
                access="private",
                content_type=content_type,
                add_random_suffix=False,
            )
        except Exception as error:
            raise BlobStorageOperationError from error
        return StoredBlob(
            pathname=result.pathname,
            content_type=result.content_type,
            size=len(body),
            etag=result.etag,
            url=result.url,
        )

    async def get(self, pathname: str) -> Any:
        try:
            result = await self.client.get(pathname, access="private")
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
