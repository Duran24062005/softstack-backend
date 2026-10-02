"""Import legacy external content media into the public content Blob Store.

Usage:
    uv run python -m scripts.migrate_content_media          # dry run
    uv run python -m scripts.migrate_content_media --apply  # persist changes
"""

from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from urllib.parse import urlparse

from pymongo import MongoClient

from app.config.config import content_blob_config, database_config
from app.services.blob_storage import VercelBlobStorage
from app.services.content_media_service import collect_document_media, import_external_url


def is_content_blob_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    configured = content_blob_config.get("PUBLIC_HOST", "")
    return bool(configured) and host.lower() == configured.lower()


async def migrate_document(document: dict, storage: VercelBlobStorage) -> tuple[dict, int]:
    migrated = 0

    async def visit(value):
        nonlocal migrated
        if isinstance(value, list):
            for item in value:
                await visit(item)
        elif isinstance(value, dict):
            node_type = value.get("type")
            if node_type in {"image", "video"} and isinstance(value.get("attrs"), dict):
                attrs = value["attrs"]
                source = attrs.get("src", "")
                if source and not is_content_blob_url(source):
                    reference = await import_external_url(storage, source, "image" if node_type == "image" else "video")
                    attrs.update({"src": reference["url"], "mediaPathname": reference["pathname"], "mediaContentType": reference["content_type"], "mediaSize": reference["size"]})
                    migrated += 1
            for child in value.values():
                await visit(child)

    content = deepcopy(document.get("content", {"type": "doc", "content": []}))
    await visit(content)
    return content, migrated


async def migrate_cover(document: dict, storage: VercelBlobStorage) -> tuple[dict | None, int]:
    cover = deepcopy(document.get("cover_media"))
    if not isinstance(cover, dict):
        return cover, 0
    source = cover.get("url", "")
    if not source or is_content_blob_url(source):
        return cover, 0
    kind = "video" if str(cover.get("content_type", "")).startswith("video/") else "image"
    reference = await import_external_url(storage, source, kind)
    return reference, 1


async def main(apply: bool) -> None:
    client = MongoClient(database_config["MONGODB_URI"])
    database = client[database_config["MONGODB_DATABASE"]]
    storage = VercelBlobStorage(config=content_blob_config)
    scanned = 0
    migrated = 0
    try:
        for lesson in database.lessons.find({"content": {"$exists": True}}):
            scanned += 1
            content, count = await migrate_document(lesson, storage)
            if count and apply:
                database.lessons.update_one({"_id": lesson["_id"]}, {"$set": {"content": content, "media_assets": collect_document_media(content)}})
            migrated += count
        for module in database.modules.find({"cover_media.url": {"$exists": True}}):
            scanned += 1
            cover, count = await migrate_cover(module, storage)
            if count and apply:
                database.modules.update_one(
                    {"_id": module["_id"]},
                    {"$set": {"cover_media": cover, "media_assets": [cover]}},
                )
            migrated += count
    finally:
        client.close()
    mode = "applied" if apply else "detected"
    print(f"Scanned {scanned} content documents; {mode} {migrated} external media references.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.apply))
