from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.core.exception import EmailNotVerifiedError
from app.services.auth_service import AuthenticationError, authenticate, register_user, update_profile
from app.core.security import decode_access_token, hash_token


def test_register_hashes_password_and_assigns_user_role():
    users = Mock(spec=UserRepository)
    users.create.side_effect = lambda document: {**document, "_id": "user-1"}

    result = register_user(users, "Person@Example.com", "strong-password")

    created = users.create.call_args.args[0]
    assert result["email"] == "person@example.com"
    assert result["role"] == "user"
    assert created["password_hash"] != "strong-password"
    assert created["password_hash"].startswith("$argon2")


def test_login_returns_tokens_and_persists_only_refresh_hash():
    users = Mock(spec=UserRepository)
    refresh_tokens = Mock(spec=RefreshTokenRepository)
    users.create.side_effect = lambda document: {**document, "_id": "user-1"}
    registered = register_user(users, "person@example.com", "strong-password")
    user = {"_id": "user-1", "email": registered["email"], "password_hash": users.create.call_args.args[0]["password_hash"], "role": "user", "is_active": True, "created_at": datetime.now(timezone.utc)}
    users.find_by_email.return_value = user

    response = authenticate(users, refresh_tokens, "PERSON@example.com", "strong-password")

    assert response["access_token"]
    assert response["refresh_token"]
    stored = refresh_tokens.create.call_args.args[0]
    assert stored["token_hash"] == hash_token(response["refresh_token"])
    assert stored["token_hash"] != response["refresh_token"]
    assert decode_access_token(response["access_token"])["type"] == "access"


def test_login_rejects_invalid_credentials():
    users = Mock(spec=UserRepository)
    users.find_by_email.return_value = None
    refresh_tokens = Mock(spec=RefreshTokenRepository)

    with pytest.raises(AuthenticationError):
        authenticate(users, refresh_tokens, "missing@example.com", "wrong-password")

    refresh_tokens.create.assert_not_called()


def test_login_rejects_unverified_email():
    users = Mock(spec=UserRepository)
    refresh_tokens = Mock(spec=RefreshTokenRepository)
    users.find_by_email.return_value = {
        "_id": "user-1",
        "email": "person@example.com",
        "password_hash": "",
        "role": "user",
        "is_active": True,
        "email_verified": False,
    }
    from app.core.security import hash_password
    users.find_by_email.return_value["password_hash"] = hash_password("strong-password")

    with pytest.raises(EmailNotVerifiedError):
        authenticate(users, refresh_tokens, "person@example.com", "strong-password")

    refresh_tokens.create.assert_not_called()


def test_profile_update_requires_current_password_for_email_and_password():
    users = Mock(spec=UserRepository)
    users.update.side_effect = lambda user_id, changes: {"_id": user_id, "email": changes.get("email", "person@example.com"), "full_name": changes.get("full_name", "Alex"), "role": "user", "is_active": True, "created_at": datetime.now(timezone.utc)}
    from app.core.security import hash_password
    user = {"_id": "user-1", "email": "person@example.com", "full_name": "Alex", "password_hash": hash_password("old-password"), "role": "user", "is_active": True, "created_at": datetime.now(timezone.utc)}

    with pytest.raises(AuthenticationError):
        update_profile(users, user, email="new@example.com", new_password="new-password")

    result = update_profile(users, user, full_name="Alex Rivera", email="new@example.com", current_password="old-password", new_password="new-password")

    assert result["email"] == "new@example.com"
    assert users.update.call_args.args[1]["full_name"] == "Alex Rivera"
