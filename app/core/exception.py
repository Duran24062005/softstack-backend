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


class EmailNotVerifiedError(ApplicationError):
    status_code = 403
    detail = "Email address must be verified before signing in"


class InvalidEmailActionTokenError(ApplicationError):
    status_code = 400
    detail = "Invalid or expired email action token"


class NotImplementedApplicationError(ApplicationError):
    status_code = 501
    detail = "Feature is not implemented yet"


class InvalidProfilePhotoError(ApplicationError):
    status_code = 400
    detail = "Invalid profile photo"


class BlobStorageUnavailableError(ApplicationError):
    status_code = 503
    detail = "Profile photo storage is unavailable"


class BlobStorageOperationError(ApplicationError):
    status_code = 502
    detail = "Could not process profile photo storage"


class ContentMediaInvalidError(ApplicationError):
    status_code = 400
    detail = "Invalid content media"


class ContentMediaUnavailableError(ApplicationError):
    status_code = 503
    detail = "Content media storage is unavailable"


class ContentMediaOperationError(ApplicationError):
    status_code = 502
    detail = "Could not process content media storage"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})
