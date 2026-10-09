from datetime import datetime, timezone

from bson import ObjectId

from app.repositories.content_revision_repository import ContentRevisionRepository


class Result:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class FakeCollection:
    def __init__(self):
        self.documents = {}

    def _matches(self, document, query):
        return all(document.get(key) == value for key, value in query.items())

    def find_one(self, query):
        return next((document for document in self.documents.values() if self._matches(document, query)), None)

    def insert_one(self, document):
        document["_id"] = ObjectId()
        self.documents[document["_id"]] = document.copy()
        return Result(document["_id"])

    def update_one(self, query, update):
        document = self.find_one(query)
        if document:
            document.update(update["$set"])

    def delete_one(self, query):
        document = self.find_one(query)
        if document:
            del self.documents[document["_id"]]


def repository():
    instance = ContentRevisionRepository.__new__(ContentRevisionRepository)
    instance.collection = FakeCollection()
    return instance


def revision_document():
    now = datetime.now(timezone.utc)
    return {
        "target_type": "lesson",
        "target_id": ObjectId(),
        "source": "ai_content_suggestion",
        "base_updated_at": now,
        "changes": {"title": "Título revisado"},
        "lesson_orders": [],
        "created_by": ObjectId(),
    }


def test_create_and_find_pending_revision_are_scoped_by_target():
    revisions = repository()
    document = revisions.create(revision_document())

    assert document["status"] == "pending"
    assert revisions.find_by_id(document["_id"]) == document
    assert revisions.find_pending(document["target_type"], document["target_id"]) == document
    assert revisions.find_pending("module", document["target_id"]) is None


def test_update_and_mark_keep_revision_state_auditable():
    revisions = repository()
    document = revisions.create(revision_document())
    updated = revisions.update(document["_id"], {"changes": {"title": "Otro título"}})

    assert updated["changes"] == {"title": "Otro título"}
    assert updated["status"] == "pending"
    assert revisions.mark(document["_id"], "published")["status"] == "published"
    assert revisions.update(document["_id"], {"changes": {"title": "No debe cambiar"}})["changes"] == {"title": "Otro título"}


def test_delete_only_removes_pending_revisions():
    revisions = repository()
    pending = revisions.create(revision_document())
    published = revisions.create(revision_document())
    revisions.mark(published["_id"], "published")

    assert revisions.delete(pending["_id"])["_id"] == pending["_id"]
    assert revisions.find_by_id(pending["_id"]) is None
    assert revisions.delete(published["_id"])["_id"] == published["_id"]
    assert revisions.find_by_id(published["_id"])["status"] == "published"
