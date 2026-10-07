from datetime import datetime, timezone

from bson import ObjectId

from app.repositories.content_repository import ProgressRepository


class Cursor(list):
    def sort(self, key, direction=1):
        return Cursor(sorted(self, key=lambda item: item[key], reverse=direction < 0))


class Collection:
    def __init__(self, database=None):
        self.database = database
        self.documents = []
        self.last_update = None

    def find(self, query):
        return Cursor([document for document in self.documents if all(document.get(key) == value for key, value in query.items())])

    def update_one(self, query, update, upsert=False):
        self.last_update = (query, update, upsert)
        document = next((item for item in self.documents if all(item.get(key) == value for key, value in query.items())), None)
        if document is None and upsert:
            document = {**query}
            self.documents.append(document)
        if document is not None:
            for key, value in update.get("$setOnInsert", {}).items():
                document.setdefault(key, value)
            document.update(update.get("$set", {}))


class Database:
    def __init__(self):
        self.progress = Collection(self)
        self.module_progress = Collection(self)


def test_progress_repository_records_completion_source_and_module_progress():
    database = Database()
    repository = ProgressRepository(database)
    user_id, lesson_id, module_id = ObjectId(), ObjectId(), ObjectId()

    repository.complete(user_id, lesson_id, module_id, source="quiz")
    repository.complete_module(user_id, module_id)

    assert database.progress.documents[0]["completion_source"] == "quiz"
    assert database.progress.last_update[2] is True
    assert repository.completed_for_user(user_id)[0]["lesson_id"] == lesson_id
    assert repository.completed_modules_for_user(user_id)[0]["module_id"] == module_id
