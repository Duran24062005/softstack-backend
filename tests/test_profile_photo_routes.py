from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import Request

from app.core.exception import InvalidTokenError
from app.routes.auth_routes import get_profile_photo, upload_profile_photo
from app.routes.dependencies import current_user
from app.services.blob_storage import StoredBlob


class RouteStorage:
    def __init__(self):
        self.deleted = []
        self.result = SimpleNamespace(content=b"private-image")

    async def upload(self, pathname, body, content_type):
        return StoredBlob(pathname, content_type, len(body), '"etag"', "private-url")

    async def get(self, pathname):
        self.pathname = pathname
        return self.result

    async def delete(self, pathname):
        self.deleted.append(pathname)


class FakeUpload:
    filename = "avatar.png"
    content_type = "image/png"

    async def read(self, _size):
        return b"\x89PNG\r\n\x1a\nimage"


def make_user(photo=None):
    user = {
        "_id": "user-1",
        "email": "person@example.com",
        "full_name": "Alex",
        "role": "user",
        "is_active": True,
        "email_verified": True,
        "created_at": datetime.now(timezone.utc),
    }
    if photo:
        user["profile_photo"] = photo
    return user


def test_profile_photo_requires_authentication():
    request = Request({"type": "http", "method": "GET", "path": "/auth/me/profile-photo", "headers": [], "query_string": b""})
    with pytest.raises(InvalidTokenError) as caught:
        current_user(request, users=SimpleNamespace())
    assert caught.value.status_code == 401


def test_profile_photo_get_streams_private_blob_for_current_user():
    photo = {"pathname": "profile-photos/user-1/photo.png", "content_type": "image/png", "etag": '"etag"'}
    storage = RouteStorage()
    response = __import__("asyncio").run(get_profile_photo(user=make_user(photo), storage=storage))

    assert response.status_code == 200
    assert response.body == b"private-image"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, no-store"
    assert storage.pathname == photo["pathname"]


def test_profile_photo_upload_accepts_multipart_and_returns_public_user_state():
    user = make_user()
    users = type("Users", (), {})()
    users.update = lambda user_id, changes: {**user, **changes, "_id": user_id}
    storage = RouteStorage()
    response = __import__("asyncio").run(upload_profile_photo(file=FakeUpload(), user=user, users=users, storage=storage))

    assert response["has_profile_photo"] is True
