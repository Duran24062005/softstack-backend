import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from bson import ObjectId

from app.config.config import content_blob_config
from app.core.exception import ContentMediaInvalidError
from app.repositories.content_media_repository import ContentMediaRepository
from app.services.content_media_service import (
    _assert_safe_external_url,
    cleanup_orphaned_media,
    collect_document_media,
    validate_cover_media,
    validate_media_reference,
)
from app.services.content_service import create_lesson, create_module


@pytest.fixture(autouse=True)
def configured_content_blob_host(monkeypatch):
    monkeypatch.setitem(content_blob_config, "PUBLIC_HOST", "store.public.blob.vercel-storage.com")


def reference(kind="image"):
    if kind == "video":
        content_type = "video/mp4"
        suffix = "video.mp4"
    else:
        content_type = "image/png"
        suffix = "image.png"
    return {
        "url": f"https://store.public.blob.vercel-storage.com/content-media/{suffix}",
        "pathname": f"content-media/{suffix}",
        "content_type": content_type,
        "size": 128,
    }


def test_collect_document_media_walks_nested_tiptap_nodes():
    image = reference("image")
    video = reference("video")
    document = {
        "type": "doc",
        "content": [
            {"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "image", "attrs": {"src": image["url"], "mediaPathname": image["pathname"], "mediaContentType": image["content_type"], "mediaSize": image["size"]}}]}]},
            {"type": "bulletList", "content": [{"type": "listItem", "content": [{"type": "video", "attrs": {"src": video["url"], "mediaPathname": video["pathname"], "mediaContentType": video["content_type"], "mediaSize": video["size"]}}]}]},
        ],
    }

    assets = collect_document_media(document)

    assert {asset["pathname"] for asset in assets} == {image["pathname"], video["pathname"]}


def test_media_reference_rejects_external_url_and_invalid_path():
    with pytest.raises(ContentMediaInvalidError):
        validate_media_reference({**reference(), "url": "https://example.com/image.png"})
    with pytest.raises(ContentMediaInvalidError):
        validate_media_reference({**reference(), "pathname": "other/image.png"})


def test_external_media_validation_rejects_private_networks():
    with pytest.raises(ContentMediaInvalidError):
        _assert_safe_external_url("http://127.0.0.1/image.png")


def test_media_reference_rejects_video_over_limit():
    with pytest.raises(ContentMediaInvalidError):
        validate_media_reference({**reference("video"), "size": 100_000_001})


def test_validates_module_cover_media():
    assert validate_cover_media(reference()) == reference()


class FakeCollection:
    def __init__(self, document=None):
        self.document = document
        self.inserted = None

    def find_one(self, *_args, **_kwargs):
        return self.document

    def insert_one(self, document):
        self.inserted = document
        return SimpleNamespace(inserted_id=document.get("_id", ObjectId()))


class FakeDatabase:
    def __init__(self, module):
        self.modules = FakeCollection(module)
        self.lessons = FakeCollection()


class FakeStorage:
    async def delete(self, _pathname):
        raise AssertionError("new media should not be deleted on a successful create")


class RecordingStorage:
    def __init__(self, blobs):
        self.blobs = blobs
        self.deleted = []

    async def list(self, _prefix):
        return self.blobs

    async def delete(self, pathname):
        self.deleted.append(pathname)


class FailingStorage:
    def __init__(self):
        self.deleted = []

    async def delete(self, pathname):
        self.deleted.append(pathname)


def test_create_lesson_persists_derived_media_assets():
    module_id = ObjectId()
    lesson_id = ObjectId()
    image = reference()
    payload = SimpleNamespace(
        title="Lección multimedia",
        description="Contenido",
        content=SimpleNamespace(model_dump=lambda: {"type": "doc", "content": [{"type": "image", "attrs": {"src": image["url"], "mediaPathname": image["pathname"], "mediaContentType": image["content_type"], "mediaSize": image["size"]}}]}),
        order=0,
        status=SimpleNamespace(value="draft"),
        estimated_minutes=10,
    )
    modules = type("Modules", (), {"find_by_id": lambda self, value: {"_id": module_id} })()
    lessons = type("Lessons", (), {"create": lambda self, document: {**document, "_id": lesson_id}})()
    repository = ContentMediaRepository(FakeDatabase(None))

    result = asyncio.run(create_lesson(modules, lessons, repository, FakeStorage(), str(module_id), payload, {"_id": ObjectId()}))

    assert result["content"]["content"][0]["attrs"]["src"] == image["url"]


def test_create_module_persists_cover_media():
    module_id = ObjectId()
    cover = reference("video")
    payload = SimpleNamespace(
        title="Módulo multimedia",
        description="Contenido",
        order=0,
        status=SimpleNamespace(value="draft"),
        cover_media=cover,
    )
    modules = type(
        "Modules",
        (),
        {"create": lambda self, document: {**document, "_id": module_id}},
    )()
    repository = ContentMediaRepository(FakeDatabase(None))

    result = asyncio.run(create_module(modules, repository, FakeStorage(), payload, {"_id": ObjectId()}))

    assert result["cover_media"] == cover


def test_cleanup_removes_only_old_unreferenced_content_blobs():
    old = datetime.now(timezone.utc) - timedelta(hours=25)
    storage = RecordingStorage([
        SimpleNamespace(pathname="content-media/old.png", uploaded_at=old),
        SimpleNamespace(pathname="content-media/referenced.png", uploaded_at=old),
        SimpleNamespace(pathname="content-media/recent.png", uploaded_at=datetime.now(timezone.utc)),
    ])
    repository = SimpleNamespace(referenced_pathnames=lambda: {"content-media/referenced.png"})

    deleted = asyncio.run(cleanup_orphaned_media(storage, repository))

    assert deleted == 1
    assert storage.deleted == ["content-media/old.png"]


def test_create_lesson_deletes_new_media_when_mongodb_write_fails():
    module_id = ObjectId()
    image = reference()
    payload = SimpleNamespace(
        title="Lección fallida",
        description="Contenido",
        content=SimpleNamespace(model_dump=lambda: {"type": "doc", "content": [{"type": "image", "attrs": {"src": image["url"], "mediaPathname": image["pathname"], "mediaContentType": image["content_type"], "mediaSize": image["size"]}}]}),
        order=0,
        status=SimpleNamespace(value="draft"),
        estimated_minutes=10,
    )
    modules = type("Modules", (), {"find_by_id": lambda self, value: {"_id": module_id}})()
    lessons = type("Lessons", (), {"create": lambda self, document: (_ for _ in ()).throw(RuntimeError("mongo unavailable"))})()
    storage = FailingStorage()
    repository = SimpleNamespace(is_referenced=lambda pathname: False)

    with pytest.raises(RuntimeError):
        asyncio.run(create_lesson(modules, lessons, repository, storage, str(module_id), payload, {"_id": ObjectId()}))

    assert storage.deleted == [image["pathname"]]
