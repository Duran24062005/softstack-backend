import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from bson import ObjectId

from app.core.exception import InvalidEmailActionTokenError
from app.repositories.user_repository import UserRepository
from app.routes.auth_routes import register, resend_verification, verify_email
from app.schemas.auth import EmailRequest, RegisterRequest
from app.services.account_email_service import AccountEmailService


def make_users():
    users = Mock(spec=UserRepository)
    created_user = {}

    def create(document):
        created_user.update(document)
        created_user["_id"] = ObjectId()
        return created_user

    users.create.side_effect = create
    users.find_by_email.side_effect = lambda _email: created_user or None
    return users


def make_email_service():
    account_email = Mock(spec=AccountEmailService)
    account_email.send_verification = AsyncMock()
    account_email.resend_verification = AsyncMock()
    account_email.verify_email = Mock()
    return account_email


def test_register_returns_verification_contract_and_sends_email():
    users = make_users()
    account_email = make_email_service()
    response = asyncio.run(
        register(
            RegisterRequest(
                full_name="Alex Rivera",
                email="PERSON@example.com",
                password="strong-password",
            ),
            users=users,
            account_email=account_email,
        )
    )

    assert response["verification_required"] is True
    assert response["message"] == "Revisa tu correo para confirmar tu cuenta."
    account_email.send_verification.assert_awaited_once()
    assert account_email.send_verification.await_args.args[0]["email"] == "person@example.com"


def test_verify_email_delegates_token_and_returns_success():
    account_email = make_email_service()
    response = verify_email("raw-token", account_email=account_email)

    assert response == {"message": "Email verificado correctamente."}
    account_email.verify_email.assert_called_once_with("raw-token")


def test_invalid_verification_token_is_exposed_as_client_error():
    account_email = make_email_service()
    account_email.verify_email.side_effect = InvalidEmailActionTokenError

    with pytest.raises(InvalidEmailActionTokenError) as caught:
        verify_email("expired-token", account_email=account_email)

    assert caught.value.status_code == 400
    assert caught.value.detail == "Invalid or expired email action token"


def test_resend_verification_is_accepted_without_disclosing_account_state():
    account_email = make_email_service()
    response = asyncio.run(
        resend_verification(
            EmailRequest(email="PERSON@example.com"),
            account_email=account_email,
        )
    )

    assert response == {"message": "Si la cuenta puede recibir un correo, enviaremos un nuevo enlace."}
    account_email.resend_verification.assert_awaited_once_with("PERSON@example.com")
