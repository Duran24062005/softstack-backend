from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.controllers.auth_controller import current_user_auth_controller
from app.config.database.mongodb_connection import get_database
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.repositories.email_action_token_repository import EmailActionTokenRepository
from app.services.account_email_service import AccountEmailService
from app.services.email_service import TransactionalEmailClient
from app.services.blob_storage import VercelBlobStorage


def get_user_repository(request: Request) -> UserRepository:
    return UserRepository(get_database(request))


def get_refresh_token_repository(request: Request) -> RefreshTokenRepository:
    return RefreshTokenRepository(get_database(request))


def get_email_action_token_repository(request: Request) -> EmailActionTokenRepository:
    return EmailActionTokenRepository(get_database(request))


def get_account_email_service(
    users: UserRepository = Depends(get_user_repository),
    action_tokens: EmailActionTokenRepository = Depends(get_email_action_token_repository),
    refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository),
) -> AccountEmailService:
    return AccountEmailService(users, action_tokens, refresh_tokens, TransactionalEmailClient())


def get_blob_storage() -> VercelBlobStorage:
    return VercelBlobStorage()


def current_user(request: Request, users: UserRepository = Depends(get_user_repository)):
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        from app.config.config import cookie_config
        token = request.cookies.get(cookie_config["ACCESS_COOKIE_NAME"], "")
        scheme = "Bearer" if token else ""
    credentials = (
        HTTPAuthorizationCredentials(scheme=scheme, credentials=token)
        if scheme.lower() == "bearer" and token
        else None
    )
    return current_user_auth_controller(credentials, users)
