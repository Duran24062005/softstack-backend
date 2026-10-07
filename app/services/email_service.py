import asyncio
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.config import email_config


class EmailServiceError(Exception):
    """Raised when the transactional email provider cannot accept a message."""


@dataclass(frozen=True)
class TransactionalEmailClient:
    base_url: str = email_config["SERVICE_URL"]
    timeout_seconds: int = email_config["REQUEST_TIMEOUT_SECONDS"]

    async def send(self, *, recipient: str, subject: str, body: str, html_body: str) -> None:
        payload = json.dumps(
            {
                "recipient": recipient,
                "subject": subject,
                "body": body,
                "html_body": html_body,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/emails/transactional",
            data=payload,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            await asyncio.to_thread(self._send_sync, request)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            raise EmailServiceError("Transactional email provider request failed") from error

    def _send_sync(self, request: Request) -> None:
        with urlopen(request, timeout=self.timeout_seconds) as response:
            if not 200 <= response.status < 300:
                raise EmailServiceError(f"Transactional email provider returned {response.status}")
