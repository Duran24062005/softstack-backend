import asyncio
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import app.services.account_email_service as account_email_module
from app.config.config import email_config
from app.core.exception import InvalidEmailActionTokenError
from app.core.security import hash_token
from app.repositories.email_action_token_repository import EmailActionTokenRepository
from app.routes.auth_routes import verify_email_code as verify_email_code_route
from app.schemas.auth import VerifyEmailCodeRequest
from app.services.account_email_service import AccountEmailService, EMAIL_VERIFICATION_CODE_PURPOSE, EMAIL_VERIFICATION_PURPOSE
from app.services.email_service import EmailServiceError


class InMemoryCollection:
    def __init__(self):
        self.documents = []

    @staticmethod
    def _matches(document, query):
        for key, expected in query.items():
            actual = document.get(key)
            if isinstance(expected, dict):
                if "$gt" in expected and not actual > expected["$gt"]:
                    return False
            elif actual != expected:
                return False
        return True

    def insert_one(self, document):
        inserted_id = f"token-{len(self.documents) + 1}"
        self.documents.append({**document, "_id": inserted_id})
        return SimpleNamespace(inserted_id=inserted_id)

    def find_one(self, query, sort=None):
        matches = [document for document in self.documents if self._matches(document, query)]
        if sort:
            for field, direction in reversed(sort):
                matches.sort(key=lambda document: document[field], reverse=direction < 0)
        return matches[0] if matches else None

    def update_many(self, query, update):
        for document in self.documents:
            if self._matches(document, query):
                document.update(update.get("$set", {}))

    def update_one(self, query, update):
        document = self.find_one(query)
        if not document:
            return
        document.update(update.get("$set", {}))
        for field, value in update.get("$inc", {}).items():
            document[field] = document.get(field, 0) + value


class InMemoryDatabase:
    def __init__(self):
        self.email_action_tokens = InMemoryCollection()


class InMemoryUsers:
    def __init__(self):
        self.user = {
            "_id": "user-1",
            "email": "person@example.com",
            "full_name": "Alex Rivera",
            "is_active": False,
            "account_status": "pending",
            "email_verified": False,
        }

    def find_by_email(self, email):
        return self.user if self.user["email"] == email else None

    def mark_email_verified(self, user_id):
        if user_id != self.user["_id"]:
            return None
        self.user["email_verified"] = True
        return self.user


class RecordingEmailClient:
    def __init__(self, *, failure=None):
        self.messages = []
        self.failure = failure

    async def send(self, **message):
        if self.failure:
            raise self.failure
        self.messages.append(message)


def make_flow(*, email_client=None):
    database = InMemoryDatabase()
    users = InMemoryUsers()
    action_tokens = EmailActionTokenRepository(database)
    client = email_client or RecordingEmailClient()
    service = AccountEmailService(users, action_tokens, Mock(), client)
    return service, users, action_tokens, client


def extract_code(client):
    return re.search(r"\b(\d{6})\b", client.messages[-1]["body"]).group(1)


def test_generated_code_is_persisted_hashed_retrievable_and_consumed_once():
    service, users, action_tokens, client = make_flow()

    asyncio.run(service.send_verification(users.user))

    code = extract_code(client)
    records = action_tokens.collection.documents
    code_record = next(record for record in records if record["purpose"] == EMAIL_VERIFICATION_CODE_PURPOSE)
    link_record = next(record for record in records if record["purpose"] == EMAIL_VERIFICATION_PURPOSE)
    assert code_record["token_hash"] == hash_token(code)
    assert code_record["token_hash"] != code
    assert code_record["attempts"] == 0
    assert code_record["expires_at"] > datetime.now(timezone.utc)

    service.verify_email_code(" PERSON@example.com ", f" {code} ")

    assert users.user["email_verified"] is True
    assert code_record["consumed_at"] is not None
    assert link_record["consumed_at"] is not None
    with pytest.raises(InvalidEmailActionTokenError):
        service.verify_email_code(users.user["email"], code)


def test_resend_invalidates_old_code_and_only_new_code_is_accepted(monkeypatch):
    service, users, action_tokens, client = make_flow()
    monkeypatch.setattr(account_email_module.secrets, "randbelow", Mock(side_effect=[123456, 654321]))

    asyncio.run(service.send_verification(users.user))
    first_code = extract_code(client)
    asyncio.run(service.resend_verification("PERSON@example.com"))
    second_code = extract_code(client)

    assert first_code == "123456"
    assert second_code == "654321"
    old_code_record = next(record for record in action_tokens.collection.documents if record["token_hash"] == hash_token(first_code))
    assert old_code_record["consumed_at"] is not None
    with pytest.raises(InvalidEmailActionTokenError):
        service.verify_email_code(users.user["email"], first_code)

    service.verify_email_code(users.user["email"], second_code)
    assert users.user["email_verified"] is True


def test_expired_code_is_not_retrieved(monkeypatch):
    service, users, action_tokens, client = make_flow()
    monkeypatch.setitem(email_config, "VERIFICATION_CODE_EXPIRE_MINUTES", 0)

    asyncio.run(service.send_verification(users.user))

    with pytest.raises(InvalidEmailActionTokenError):
        service.verify_email_code(users.user["email"], extract_code(client))
    assert action_tokens.collection.documents[1]["consumed_at"] is None
    assert users.user["email_verified"] is False


def test_wrong_codes_are_counted_and_blocked_after_configured_attempts(monkeypatch):
    service, users, action_tokens, client = make_flow()
    monkeypatch.setitem(email_config, "VERIFICATION_MAX_ATTEMPTS", 2)

    asyncio.run(service.send_verification(users.user))
    code_record = action_tokens.collection.documents[1]

    for _ in range(2):
        with pytest.raises(InvalidEmailActionTokenError):
            service.verify_email_code(users.user["email"], "000000")

    assert code_record["attempts"] == 2
    with pytest.raises(InvalidEmailActionTokenError):
        service.verify_email_code(users.user["email"], extract_code(client))
    assert code_record["attempts"] == 2
    assert users.user["email_verified"] is False


def test_provider_failure_keeps_persisted_code_available_for_resend():
    failing_client = RecordingEmailClient(failure=EmailServiceError("provider unavailable"))
    service, users, action_tokens, _ = make_flow(email_client=failing_client)

    asyncio.run(service.send_verification(users.user))

    assert len(action_tokens.collection.documents) == 2
    assert all(record["consumed_at"] is None for record in action_tokens.collection.documents)


def test_route_accepts_the_code_persisted_by_registration():
    service, users, _, client = make_flow()
    asyncio.run(service.send_verification(users.user))
    code = extract_code(client)

    response = verify_email_code_route(
        VerifyEmailCodeRequest(email=users.user["email"], code=code),
        account_email=service,
    )

    assert response == {"message": "Email verificado correctamente."}
    assert users.user["email_verified"] is True


def test_route_schema_rejects_malformed_codes_before_service_lookup():
    service, users, _, _ = make_flow()
    with pytest.raises(ValueError):
        VerifyEmailCodeRequest(email=users.user["email"], code="12A")
    assert users.user["email_verified"] is False
