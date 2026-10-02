import asyncio
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.core.exception import InvalidEmailActionTokenError
from app.core.security import hash_token
from app.repositories.email_action_token_repository import EmailActionTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services.account_email_service import AccountEmailService


class FakeEmailClient:
    def __init__(self):
        self.messages = []

    async def send(self, **message):
        self.messages.append(message)


def make_service():
    users = Mock(spec=UserRepository)
    action_tokens = Mock(spec=EmailActionTokenRepository)
    refresh_tokens = Mock(spec=RefreshTokenRepository)
    client = FakeEmailClient()
    service = AccountEmailService(users, action_tokens, refresh_tokens, client)
    return service, users, action_tokens, refresh_tokens, client


def test_verification_email_stores_hash_and_verifies_once():
    service, users, action_tokens, _, client = make_service()
    user_id = SimpleNamespace(__str__=lambda self: "user-1")
    user = {"_id": user_id, "email": "person@example.com", "full_name": "Alex", "is_active": True, "email_verified": False}
    users.find_by_email.return_value = user
    users.mark_email_verified.return_value = user

    asyncio.run(service.send_verification(user))

    stored = action_tokens.create.call_args.args[0]
    assert stored["purpose"] == "email_verification"
    assert stored["token_hash"]
    assert stored["token_hash"] != client.messages[0]["html_body"]

    token = re.search(r"token=([^\"]+)", client.messages[0]["html_body"]).group(1)
    action_tokens.find_active_by_hash.return_value = {"_id": "token-1", "user_id": user_id}
    service.verify_email(token)

    users.mark_email_verified.assert_called_once_with(user_id)
    action_tokens.consume.assert_called_once_with("token-1")


def test_reset_password_consumes_code_and_revokes_sessions():
    service, users, action_tokens, refresh_tokens, client = make_service()
    user_id = "user-1"
    user = {"_id": user_id, "email": "person@example.com", "is_active": True}
    users.find_by_email.return_value = user
    action_tokens.find_active_for_user.return_value = {
        "_id": "token-1",
        "user_id": user_id,
        "token_hash": "placeholder",
        "attempts": 0,
        "expires_at": datetime.now(timezone.utc),
    }

    asyncio.run(service.request_password_reset(user["email"]))
    code = re.search(r"\b(\d{6})\b", client.messages[0]["body"]).group(1)
    action_tokens.find_active_for_user.return_value["token_hash"] = hash_token(code)
    users.update.return_value = user

    service.reset_password(user["email"], code, "new-password-123")

    assert users.update.call_args.args[1]["password_hash"] != "new-password-123"
    action_tokens.consume.assert_called_once_with("token-1")
    refresh_tokens.revoke_for_user.assert_called_once_with(user_id)


def test_reset_password_increments_attempts_for_wrong_code():
    service, users, action_tokens, _, _ = make_service()
    users.find_by_email.return_value = {"_id": "user-1", "email": "person@example.com", "is_active": True}
    action_tokens.find_active_for_user.return_value = {"_id": "token-1", "token_hash": hash_token("123456"), "attempts": 0}

    with pytest.raises(InvalidEmailActionTokenError):
        service.reset_password("person@example.com", "999999", "new-password-123")

    action_tokens.increment_attempts.assert_called_once_with("token-1")
