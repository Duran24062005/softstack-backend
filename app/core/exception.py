from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApplicationError(Exception):
    status_code = 500
    detail = "Internal application error"


class AuthenticationError(ApplicationError):
    status_code = 401
    detail = "Invalid email or password"


class AuthorizationError(ApplicationError):
    status_code = 403
    detail = "Insufficient permissions"


class ConflictError(ApplicationError):
    status_code = 409
    detail = "Resource already exists"


class NotFoundError(ApplicationError):
    status_code = 404
    detail = "Resource not found"


class InvalidTokenError(ApplicationError):
    status_code = 401
    detail = "Invalid authentication credentials"


class InactiveUserError(ApplicationError):
    status_code = 403
    detail = "User is inactive or unavailable"


class NotImplementedApplicationError(ApplicationError):
    status_code = 501
    detail = "Feature is not implemented yet"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
