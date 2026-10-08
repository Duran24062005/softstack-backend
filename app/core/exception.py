from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApplicationError(Exception):
    status_code = 500
    detail = "Internal application error"
    code: str | None = None


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


class AccountPendingApprovalError(ApplicationError):
    status_code = 403
    detail = "Tu cuenta está pendiente de aprobación administrativa"


class AccountRejectedError(ApplicationError):
    status_code = 403
    detail = "Tu cuenta no fue aprobada por la administración"


class InvalidAccountStatusTransitionError(ApplicationError):
    status_code = 409
    detail = "Invalid account status transition"


class EmailNotVerifiedError(ApplicationError):
    status_code = 403
    detail = "Email address must be verified before signing in"
    code = "EMAIL_NOT_VERIFIED"


class InvalidEmailActionTokenError(ApplicationError):
    status_code = 400
    detail = "Invalid or expired email action token"


class NotImplementedApplicationError(ApplicationError):
    status_code = 501
    detail = "Feature is not implemented yet"


class InvalidProfilePhotoError(ApplicationError):
    status_code = 400
    detail = "Invalid profile photo"


class InvalidStudentAcademicProfileError(ApplicationError):
    status_code = 422
    detail = "La información académica del estudiante es obligatoria y válida"


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


class AssessmentUnavailableError(ApplicationError):
    status_code = 409
    detail = "This assessment is not ready for students"


class AttemptLimitError(ApplicationError):
    status_code = 409
    detail = "No attempts remain for this assessment"


class InvalidAssessmentAnswerError(ApplicationError):
    status_code = 400
    detail = "The submitted assessment answers are invalid"


class AIProviderUnavailableError(ApplicationError):
    status_code = 503
    detail = "The question suggestion provider is unavailable"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error_handler(_: Request, error: ApplicationError) -> JSONResponse:
        content = {"detail": error.detail}
        if error.code:
            content["code"] = error.code
        return JSONResponse(status_code=error.status_code, content=content)
