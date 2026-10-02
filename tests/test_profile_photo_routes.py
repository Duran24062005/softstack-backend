from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception import InvalidTokenError, register_exception_handlers
from app.repositories.user_repository import UserRepository
from app.routes.auth_routes import router
from app.routes.dependencies import current_user, get_blob_storage, get_user_repository
from app.services.blob_storage import StoredBlob


class RouteStorage:
    def __init__(self):
        self.deleted = []
        self.result = SimpleNamespace(stream=[b"private-image"])

    async def upload(self, pathname, body, content_type):
        return StoredBlob(pathname, content_type, len(body), '"etag"', "private-url")

    async def get(self, pathname):
        self.pathname = pathname
        return self.result

    async def delete(self, pathname):
        self.deleted.append(pathname)


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


def make_app(user, users, storage):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[current_user] = lambda: user
    app.dependency_overrides[get_user_repository] = lambda: users
    app.dependency_overrides[get_blob_storage] = lambda: storage
    return app


def test_profile_photo_requires_authentication():
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    def deny():
        raise InvalidTokenError

    app.dependency_overrides[current_user] = deny

    with TestClient(app) as client:
        response = client.get("/auth/me/profile-photo")

    assert response.status_code == 401


def test_profile_photo_get_streams_private_blob_for_current_user():
    photo = {"pathname": "profile-photos/user-1/photo.png", "content_type": "image/png", "etag": '"etag"'}
    storage = RouteStorage()
    app = make_app(make_user(photo), None, storage)

    with TestClient(app) as client:
        response = client.get("/auth/me/profile-photo")

    assert response.status_code == 200
    assert response.content == b"private-image"
    assert response.headers["content-type"] == "image/png"
    assert response.headers["cache-control"] == "private, no-store"
    assert storage.pathname == photo["pathname"]


def test_profile_photo_upload_accepts_multipart_and_returns_public_user_state():
    user = make_user()
    users = type("Users", (), {})()
    users.update = lambda user_id, changes: {**user, **changes, "_id": user_id}
    storage = RouteStorage()
    app = make_app(user, users, storage)

    with TestClient(app) as client:
        response = client.post(
            "/auth/me/profile-photo",
            files={"file": ("avatar.png", b"\x89PNG\r\n\x1a\nimage", "image/png")},
        )

    assert response.status_code == 200
    assert response.json()["has_profile_photo"] is True
