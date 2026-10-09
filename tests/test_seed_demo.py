from __future__ import annotations

import re
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

from bson import ObjectId
import pytest

from scripts.seed_demo import DEMO_NAMESPACE, DEMO_USERS, seed_demo


class FakeCursor(list):
    def sort(self, key: str, direction: int = 1):
        return FakeCursor(sorted(self, key=lambda item: item.get(key), reverse=direction < 0))


class FakeCollection:
    def __init__(self):
        self.documents: list[dict[str, Any]] = []

    def create_index(self, *_args, **_kwargs):
        return None

    def _matches(self, document: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, expected in query.items():
            value = document.get(key)
            if isinstance(expected, dict) and "$regex" in expected:
                if not re.search(expected["$regex"], str(value or "")):
                    return False
            elif value != expected:
                return False
        return True

    def find_one(self, query: dict[str, Any]):
        return next((document for document in self.documents if self._matches(document, query)), None)

    def find(self, query: dict[str, Any] | None = None):
        return FakeCursor([document for document in self.documents if not query or self._matches(document, query)])

    def insert_one(self, document: dict[str, Any]):
        stored = dict(document)
        stored.setdefault("_id", ObjectId())
        self.documents.append(stored)
        return SimpleNamespace(inserted_id=stored["_id"])

    def update_one(self, query: dict[str, Any], changes: dict[str, Any], upsert: bool = False):
        document = self.find_one(query)
        inserted = False
        if document is None and upsert:
            document = {key: value for key, value in query.items() if not isinstance(value, dict)}
            self.insert_one(document)
            document = self.documents[-1]
            inserted = True
        if document is None:
            return SimpleNamespace(matched_count=0)
        for key, value in changes.get("$set", {}).items():
            document[key] = value
        if inserted:
            for key, value in changes.get("$setOnInsert", {}).items():
                document.setdefault(key, value)
        return SimpleNamespace(matched_count=1)

    def find_one_and_update(self, query: dict[str, Any], changes: dict[str, Any], upsert: bool = False, return_document=None):
        document = self.find_one(query)
        if document is None and upsert:
            document = {key: value for key, value in query.items()}
            self.insert_one(document)
            document = self.documents[-1]
            for key, value in changes.get("$setOnInsert", {}).items():
                document[key] = value
        if document is None:
            return None
        for key, value in changes.get("$set", {}).items():
            document[key] = value
        return document

    def count_documents(self, query: dict[str, Any]):
        return len([document for document in self.documents if self._matches(document, query)])


class FakeDatabase:
    def __init__(self):
        self._collections: dict[str, FakeCollection] = {}

    def __getattr__(self, name: str):
        if name not in self._collections:
            self._collections[name] = FakeCollection()
        return self._collections[name]


def test_demo_fixture_has_expected_roles_and_is_repeatable():
    assert [user["role"] for user in DEMO_USERS] == ["admin", "trainer", "user", "user", "user", "user"]
    assert [user["account_status"] for user in DEMO_USERS].count("active") == 5
    assert [user["account_status"] for user in DEMO_USERS].count("pending") == 1

    database = FakeDatabase()
    now = datetime(2026, 10, 9, tzinfo=timezone.utc)
    first = seed_demo(database, "SoftStackDemo2026!", now)
    counts_after_first = {name: len(collection.documents) for name, collection in database._collections.items()}
    second = seed_demo(database, "SoftStackDemo2026!", now)
    counts_after_second = {name: len(collection.documents) for name, collection in database._collections.items()}

    assert first == second
    assert counts_after_first == counts_after_second
    assert first == {"users": 6, "modules": 5, "lessons": 13, "assessments": 18, "questions": 90}
    assert database.questions.count_documents({"demo_seed_key": {"$regex": f"^{DEMO_NAMESPACE}:"}}) == 90


def test_demo_fixture_refuses_to_replace_a_non_demo_account():
    database = FakeDatabase()
    database.users.insert_one({"email": "admin@softstack.test", "demo_seed_key": "external-account"})

    with pytest.raises(RuntimeError, match="Refusing to overwrite non-demo user"):
        seed_demo(database, "SoftStackDemo2026!", datetime(2026, 10, 9, tzinfo=timezone.utc))

    assert len(database.modules.documents) == 0
