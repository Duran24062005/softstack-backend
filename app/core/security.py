import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.config.config import security_config

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(user_id: str, role: str) -> tuple[str, int]:
    expires = timedelta(minutes=security_config["ACCESS_TOKEN_EXPIRE_MINUTES"])
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {"sub": user_id, "type": "access", "role": role, "iat": now, "exp": now + expires, "jti": secrets.token_hex(16)}
    return jwt.encode(payload, security_config["JWT_SECRET_KEY"], algorithm=security_config["JWT_ALGORITHM"]), int(expires.total_seconds())


def create_refresh_token(user_id: str, role: str) -> tuple[str, datetime]:
    expires = datetime.now(timezone.utc) + timedelta(days=security_config["REFRESH_TOKEN_EXPIRE_DAYS"])
    payload: dict[str, Any] = {"sub": user_id, "type": "refresh", "role": role, "iat": datetime.now(timezone.utc), "exp": expires, "jti": secrets.token_hex(16)}
    return jwt.encode(payload, security_config["JWT_SECRET_KEY"], algorithm=security_config["JWT_ALGORITHM"]), expires


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, security_config["JWT_SECRET_KEY"], algorithms=[security_config["JWT_ALGORITHM"]])
    if payload.get("type") != "access" or not payload.get("sub"):
        raise jwt.InvalidTokenError("invalid access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, security_config["JWT_SECRET_KEY"], algorithms=[security_config["JWT_ALGORITHM"]])
    if payload.get("type") != "refresh" or not payload.get("sub"):
        raise jwt.InvalidTokenError("invalid refresh token")
    return payload
