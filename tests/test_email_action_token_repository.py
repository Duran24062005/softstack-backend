from datetime import datetime, timezone
from types import SimpleNamespace

from app.repositories.email_action_token_repository import EmailActionTokenRepository


class CollectionDouble:
    def __init__(self):
        self.find_one_calls = []
        self.update_many_calls = []
        self.update_one_calls = []

    def find_one(self, query, sort=None):
        self.find_one_calls.append((query, sort))
        return {"_id": "token-1"}

    def insert_one(self, document):
        return SimpleNamespace(inserted_id="token-1")

    def update_many(self, query, update):
        self.update_many_calls.append((query, update))

    def update_one(self, query, update):
        self.update_one_calls.append((query, update))


class DatabaseDouble:
    def __init__(self):
        self.email_action_tokens = CollectionDouble()


def test_repository_persists_and_returns_active_token_queries():
    database = DatabaseDouble()
    repository = EmailActionTokenRepository(database)
    document = {"user_id": "user-1", "purpose": "email_verification_code"}

    created = repository.create(document)
    by_hash = repository.find_active_by_hash("hash", "email_verification_code")
    by_user = repository.find_active_by_user_and_purpose("user-1", "email_verification_code")

    assert created["_id"] == "token-1"
    assert document["_id"] == "token-1"
    assert by_hash == {"_id": "token-1"}
    assert by_user == {"_id": "token-1"}
    hash_query, _ = database.email_action_tokens.find_one_calls[0]
    assert hash_query["token_hash"] == "hash"
    assert hash_query["purpose"] == "email_verification_code"
    assert hash_query["consumed_at"] is None
    assert isinstance(hash_query["expires_at"]["$gt"], datetime)
    user_query, _ = database.email_action_tokens.find_one_calls[1]
    assert user_query["user_id"] == "user-1"
    assert user_query["purpose"] == "email_verification_code"
    assert user_query["consumed_at"] is None
    assert isinstance(user_query["expires_at"]["$gt"], datetime)
    assert database.email_action_tokens.find_one_calls[1][1] == [("created_at", -1)]


def test_repository_invalidates_increments_and_consumes_tokens():
    database = DatabaseDouble()
    repository = EmailActionTokenRepository(database)

    repository.invalidate_active("user-1", "email_verification_code")
    repository.increment_attempts("token-1")
    repository.consume("token-1")

    invalidate_query, invalidate_update = database.email_action_tokens.update_many_calls[0]
    assert invalidate_query == {"user_id": "user-1", "purpose": "email_verification_code", "consumed_at": None}
    assert set(invalidate_update["$set"]) == {"consumed_at"}
    assert invalidate_update["$set"]["consumed_at"].tzinfo == timezone.utc
    assert database.email_action_tokens.update_one_calls[0] == ({"_id": "token-1"}, {"$inc": {"attempts": 1}})
    assert database.email_action_tokens.update_one_calls[1][0] == {"_id": "token-1", "consumed_at": None}
    assert set(database.email_action_tokens.update_one_calls[1][1]["$set"]) == {"consumed_at"}
