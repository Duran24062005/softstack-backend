import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exception import InvalidProfilePhotoError, NotFoundError
from app.repositories.user_repository import UserRepository
from app.services.blob_storage import StoredBlob
from app.services.profile_photo_service import ProfilePhotoService


class FakeUpload:
    def __init__(self, body: bytes, content_type: str):
        self.body = body
        self.content_type = content_type

    async def read(self, _: int) -> bytes:
        return self.body


class FakeStorage:
    def __init__(self):
        self.uploads = []
        self.deleted = []
        self.result = SimpleNamespace(stream=[b"image-bytes"])

    async def upload(self, pathname: str, body: bytes, content_type: str) -> StoredBlob:
        self.uploads.append((pathname, body, content_type))
        return StoredBlob(pathname, content_type, len(body), '"etag"', "private-url")

    async def get(self, pathname: str):
        self.deleted.append(("get", pathname))
        return self.result

    async def delete(self, pathname: str) -> None:
        self.deleted.append(pathname)


def user_with_photo(photo=None):
    user = {
        "_id": "user-1",
        "email": "person@example.com",
        "full_name": "Alex",
        "role": "user",
        "is_active": True,
        "email_verified": True,
        "created_at": SimpleNamespace(),
    }
    if photo is not None:
        user["profile_photo"] = photo
    return user


def test_upload_validates_signature_and_persists_metadata():
    users = Mock(spec=UserRepository)
    storage = FakeStorage()
    user = user_with_photo()
    users.update.side_effect = lambda user_id, changes: {**user, **changes, "_id": user_id}

    result = asyncio.run(ProfilePhotoService(users, storage).upload(user, FakeUpload(b"\x89PNG\r\n\x1a\nimage", "image/png")))

    assert result["has_profile_photo"] is True
    assert storage.uploads[0][0].startswith("profile-photos/user-1/")
    assert users.update.call_args.args[1]["profile_photo"]["content_type"] == "image/png"


def test_upload_rejects_mismatched_signature_and_does_not_call_storage():
    users = Mock(spec=UserRepository)
    storage = FakeStorage()

    with pytest.raises(InvalidProfilePhotoError):
        asyncio.run(ProfilePhotoService(users, storage).upload(user_with_photo(), FakeUpload(b"not-an-image", "image/jpeg")))

    assert storage.uploads == []


def test_upload_rejects_files_over_three_megabytes():
    users = Mock(spec=UserRepository)
    storage = FakeStorage()
    body = b"\xff\xd8\xff" + b"x" * 3_000_000

    with pytest.raises(InvalidProfilePhotoError):
        asyncio.run(ProfilePhotoService(users, storage).upload(user_with_photo(), FakeUpload(body, "image/jpeg")))


def test_replacing_photo_deletes_the_previous_blob():
    old_photo = {"pathname": "profile-photos/user-1/old.jpg", "content_type": "image/jpeg"}
    users = Mock(spec=UserRepository)
    storage = FakeStorage()
    old_user = user_with_photo(old_photo)
    users.update.side_effect = lambda user_id, changes: {**old_user, **changes, "_id": user_id}

    asyncio.run(ProfilePhotoService(users, storage).upload(old_user, FakeUpload(b"\xff\xd8\xffimage", "image/jpeg")))

    assert old_photo["pathname"] in storage.deleted


def test_delete_clears_database_and_blob():
    old_photo = {"pathname": "profile-photos/user-1/old.webp", "content_type": "image/webp"}
    users = Mock(spec=UserRepository)
    storage = FakeStorage()
    old_user = user_with_photo(old_photo)
    users.update.side_effect = lambda user_id, changes: {**old_user, **changes, "_id": user_id}

    result = asyncio.run(ProfilePhotoService(users, storage).delete(old_user))

    assert result["has_profile_photo"] is False
    assert users.update.call_args.args[1] == {"profile_photo": None}
    assert old_photo["pathname"] in storage.deleted


def test_get_only_reads_the_photo_from_the_current_user_record():
    photo = {"pathname": "profile-photos/user-1/current.png", "content_type": "image/png"}
    storage = FakeStorage()

    result, metadata = asyncio.run(ProfilePhotoService(None, storage).get(user_with_photo(photo)))

    assert result is storage.result
    assert metadata == photo
    assert ("get", photo["pathname"]) in storage.deleted


def test_get_without_photo_returns_not_found():
    with pytest.raises(NotFoundError):
        asyncio.run(ProfilePhotoService(None, FakeStorage()).get(user_with_photo()))
