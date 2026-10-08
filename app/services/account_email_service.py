import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.config.config import email_config
from app.core.exception import InvalidEmailActionTokenError
from app.core.security import hash_password, hash_token
from app.repositories.email_action_token_repository import EmailActionTokenRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.models.auth import AccountStatus, effective_account_status
from app.services.email_service import EmailServiceError, TransactionalEmailClient

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_PURPOSE = "email_verification"
PASSWORD_RESET_PURPOSE = "password_reset"


class AccountEmailService:
    def __init__(
        self,
        users: UserRepository,
        action_tokens: EmailActionTokenRepository,
        refresh_tokens: RefreshTokenRepository,
        email_client: TransactionalEmailClient,
    ):
        self.users = users
        self.action_tokens = action_tokens
        self.refresh_tokens = refresh_tokens
        self.email_client = email_client

    async def send_verification(self, user: dict) -> None:
        raw_token = secrets.token_urlsafe(32)
        self.action_tokens.invalidate_active(user["_id"], EMAIL_VERIFICATION_PURPOSE)
        self.action_tokens.create(self._token_document(user["_id"], raw_token, EMAIL_VERIFICATION_PURPOSE, email_config["VERIFICATION_EXPIRE_MINUTES"]))
        verify_url = f"{email_config['FRONTEND_URL']}/verify-email?token={quote(raw_token)}"
        try:
            await self.email_client.send(
                recipient=user["email"],
                subject="Confirma tu cuenta de SoftStack",
                body=f"Hola {user['full_name'] or user['email']}, confirma tu cuenta aquí: {verify_url}",
                html_body=(
                    f"<p>Hola {user['full_name'] or user['email']},</p>"
                    f"<p>Confirma tu cuenta de SoftStack haciendo clic en este enlace:</p>"
                    f"<p><a href=\"{verify_url}\">Confirmar mi cuenta</a></p>"
                ),
            )
        except EmailServiceError:
            logger.exception("Verification email could not be delivered", extra={"user_id": str(user["_id"])})

    async def resend_verification(self, email: str) -> None:
        user = self.users.find_by_email(email.lower())
        if user and effective_account_status(user) in {AccountStatus.PENDING, AccountStatus.ACTIVE} and not user.get("email_verified", True):
            await self.send_verification(user)

    def verify_email(self, raw_token: str) -> None:
        record = self.action_tokens.find_active_by_hash(hash_token(raw_token), EMAIL_VERIFICATION_PURPOSE)
        if not record:
            raise InvalidEmailActionTokenError
        updated = self.users.mark_email_verified(record["user_id"])
        if not updated:
            raise InvalidEmailActionTokenError
        self.action_tokens.consume(record["_id"])

    async def request_password_reset(self, email: str) -> None:
        user = self.users.find_by_email(email.lower())
        if not user or effective_account_status(user) != AccountStatus.ACTIVE:
            return

        code = f"{secrets.randbelow(1_000_000):06d}"
        self.action_tokens.invalidate_active(user["_id"], PASSWORD_RESET_PURPOSE)
        self.action_tokens.create(self._token_document(user["_id"], code, PASSWORD_RESET_PURPOSE, email_config["RESET_CODE_EXPIRE_MINUTES"], attempts=0))
        try:
            await self.email_client.send(
                recipient=user["email"],
                subject="Tu código para recuperar SoftStack",
                body=f"Tu código de recuperación es {code}. Caduca en {email_config['RESET_CODE_EXPIRE_MINUTES']} minutos.",
                html_body=(
                    f"<p>Tu código de recuperación de SoftStack es:</p>"
                    f"<p style=\"font-size: 28px; letter-spacing: 6px; font-weight: 700;\">{code}</p>"
                    f"<p>Caduca en {email_config['RESET_CODE_EXPIRE_MINUTES']} minutos.</p>"
                ),
            )
        except EmailServiceError:
            logger.exception("Password reset email could not be delivered", extra={"user_id": str(user["_id"])})

    def reset_password(self, email: str, code: str, new_password: str) -> None:
        user = self.users.find_by_email(email.lower())
        record = user and self.action_tokens.find_active_for_user(user["_id"], PASSWORD_RESET_PURPOSE)
        if not user or not record or record.get("attempts", 0) >= email_config["RESET_MAX_ATTEMPTS"]:
            raise InvalidEmailActionTokenError

        if not secrets.compare_digest(record["token_hash"], hash_token(code)):
            self.action_tokens.increment_attempts(record["_id"])
            raise InvalidEmailActionTokenError

        updated = self.users.update(user["_id"], {"password_hash": hash_password(new_password)})
        if not updated:
            raise InvalidEmailActionTokenError
        self.action_tokens.consume(record["_id"])
        self.refresh_tokens.revoke_for_user(user["_id"])

    @staticmethod
    def _token_document(user_id, raw_token: str, purpose: str, expires_minutes: int, *, attempts: int = 0) -> dict:
        now = datetime.now(timezone.utc)
        return {
            "user_id": user_id,
            "purpose": purpose,
            "token_hash": hash_token(raw_token),
            "expires_at": now + timedelta(minutes=expires_minutes),
            "created_at": now,
            "consumed_at": None,
            "attempts": attempts,
        }
