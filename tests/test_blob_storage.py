import asyncio
from types import SimpleNamespace

from app.services.blob_storage import VercelBlobStorage


class FakeBlobClient:
    async def put(self, *_args, **_kwargs):
        return SimpleNamespace(
            pathname="profile-photos/user-1/photo.png",
            content_type="image/png",
            url="https://blob.example/photo.png",
        )


def test_upload_accepts_put_result_without_etag():
    storage = VercelBlobStorage(client=FakeBlobClient())

    result = asyncio.run(storage.upload("profile-photos/user-1/photo.png", b"image", "image/png"))

    assert result.pathname == "profile-photos/user-1/photo.png"
    assert result.etag == ""
