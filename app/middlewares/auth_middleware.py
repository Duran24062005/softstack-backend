from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_access_token


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.auth_payload = None
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            try:
                request.state.auth_payload = decode_access_token(token)
            except Exception:
                request.state.auth_payload = None
        return await call_next(request)


def add_auth_middleware(app) -> None:
    app.add_middleware(AuthMiddleware)
