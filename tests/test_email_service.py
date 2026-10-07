import asyncio
import json
from unittest.mock import patch
from urllib.error import URLError

import pytest

from app.services.email_service import EmailServiceError, TransactionalEmailClient


class FakeResponse:
    def __init__(self, status: int):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


async def run_in_place(function, *args, **kwargs):
    return function(*args, **kwargs)


def send_message(client: TransactionalEmailClient) -> None:
    asyncio.run(
        client.send(
            recipient="person@example.com",
            subject="Confirma tu cuenta",
            body="Confirma tu cuenta aquí: https://frontend.example/verify-email?token=abc",
            html_body='<p><a href="https://frontend.example/verify-email?token=abc">Confirmar</a></p>',
        )
    )


def test_transactional_client_matches_provider_contract():
    client = TransactionalEmailClient(
        base_url="https://email-provider.example",
        timeout_seconds=7,
    )

    with patch("app.services.email_service.asyncio.to_thread", new=run_in_place), patch(
        "app.services.email_service.urlopen", return_value=FakeResponse(202)
    ) as urlopen:
        send_message(client)

    request, = urlopen.call_args.args
    headers = {name.lower(): value for name, value in request.header_items()}

    assert request.full_url == "https://email-provider.example/emails/transactional"
    assert request.method == "POST"
    assert headers["content-type"] == "application/json"
    assert "x-internal-api-key" not in headers
    assert json.loads(request.data) == {
        "recipient": "person@example.com",
        "subject": "Confirma tu cuenta",
        "body": "Confirma tu cuenta aquí: https://frontend.example/verify-email?token=abc",
        "html_body": '<p><a href="https://frontend.example/verify-email?token=abc">Confirmar</a></p>',
    }
    assert urlopen.call_args.kwargs == {"timeout": 7}


def test_transactional_client_is_public_and_does_not_require_api_key():
    client = TransactionalEmailClient(base_url="https://email-provider.example")

    with patch("app.services.email_service.asyncio.to_thread", new=run_in_place), patch(
        "app.services.email_service.urlopen", return_value=FakeResponse(202)
    ) as urlopen:
        send_message(client)

    urlopen.assert_called_once()


def test_transactional_client_reports_provider_status_errors():
    client = TransactionalEmailClient(base_url="https://email-provider.example")

    with patch("app.services.email_service.asyncio.to_thread", new=run_in_place), patch(
        "app.services.email_service.urlopen", return_value=FakeResponse(503)
    ):
        with pytest.raises(EmailServiceError, match="returned 503"):
            send_message(client)


def test_transactional_client_normalizes_network_errors():
    client = TransactionalEmailClient(base_url="https://email-provider.example")

    with patch("app.services.email_service.asyncio.to_thread", new=run_in_place), patch(
        "app.services.email_service.urlopen", side_effect=URLError("provider unavailable")
    ):
        with pytest.raises(EmailServiceError, match="request failed"):
            send_message(client)
