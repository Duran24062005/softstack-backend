from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from fastapi.responses import Response

from app.controllers.auth_controller import (
    current_user_controller,
    login_controller,
    refresh_controller,
    register_user_controller,
    update_profile_controller,
)
from app.config.config import cookie_config
from app.core.cookies import clear_auth_cookies, set_auth_cookies
from app.core.exception import EmailNotVerifiedError, InvalidTokenError
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.routes.dependencies import current_user, get_account_email_service, get_blob_storage, get_refresh_token_repository, get_user_repository
from app.schemas.auth import AuthResponse, EmailRequest, LoginRequest, ProfileUpdateRequest, RegisterRequest, ResetPasswordRequest, UserResponse, VerifyEmailCodeRequest
from app.schemas.student_profile import AcademicProfileInput, AcademicProfileResponse
from app.services.account_email_service import AccountEmailService
from app.services.student_profile_service import get_academic_profile, save_academic_profile
from app.middlewares.role_middleware import require_roles
from app.services.blob_storage import VercelBlobStorage
from app.services.profile_photo_service import ProfilePhotoService

router = APIRouter(prefix="/auth", tags=["authentication"])
student = require_roles("user")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    users: UserRepository = Depends(get_user_repository),
    account_email: AccountEmailService = Depends(get_account_email_service),
):
    registered = register_user_controller(users, payload.email, payload.password, payload.full_name, payload.academic_profile.model_dump(mode="json") if payload.academic_profile else None)
    user = users.find_by_email(str(payload.email).lower())
    if user:
        await account_email.send_verification(user)
    return {
        "expires_in": 0,
        "user": registered,
        "verification_required": True,
        "message": "Revisa tu correo para confirmar tu cuenta.",
    }


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    users: UserRepository = Depends(get_user_repository),
    refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository),
    account_email: AccountEmailService = Depends(get_account_email_service),
):
    try:
        session = login_controller(users, refresh_tokens, payload.email, payload.password)
    except EmailNotVerifiedError:
        # The password was correct, so the user can recover even when the
        # original registration email was never delivered.
        await account_email.resend_verification(str(payload.email))
        raise
    set_auth_cookies(response, session["access_token"], session["refresh_token"])
    return {"expires_in": session["expires_in"], "user": session["user"]}


@router.post("/refresh", response_model=AuthResponse)
def refresh(request: Request, response: Response, users: UserRepository = Depends(get_user_repository), refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository)):
    token = request.cookies.get(cookie_config["REFRESH_COOKIE_NAME"])
    if not token:
        raise InvalidTokenError
    session = refresh_controller(users, refresh_tokens, token)
    set_auth_cookies(response, session["access_token"], session["refresh_token"])
    return {"expires_in": session["expires_in"], "user": session["user"]}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, refresh_tokens: RefreshTokenRepository = Depends(get_refresh_token_repository)):
    token = request.cookies.get(cookie_config["REFRESH_COOKIE_NAME"])
    if token:
        from app.core.security import hash_token
        refresh_tokens.revoke(hash_token(token))
    clear_auth_cookies(response)
    return None


@router.get("/verify-email")
def verify_email(token: str, account_email: AccountEmailService = Depends(get_account_email_service)):
    account_email.verify_email(token)
    return {"message": "Email verificado correctamente."}


@router.post("/verify-email-code")
def verify_email_code(payload: VerifyEmailCodeRequest, account_email: AccountEmailService = Depends(get_account_email_service)):
    account_email.verify_email_code(str(payload.email), payload.code)
    return {"message": "Email verificado correctamente."}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
async def resend_verification(payload: EmailRequest, account_email: AccountEmailService = Depends(get_account_email_service)):
    await account_email.resend_verification(str(payload.email))
    return {"message": "Si la cuenta puede recibir un correo, enviaremos un nuevo enlace y código."}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(payload: EmailRequest, account_email: AccountEmailService = Depends(get_account_email_service)):
    await account_email.request_password_reset(str(payload.email))
    return {"message": "Si la cuenta existe, enviaremos un código de recuperación."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, account_email: AccountEmailService = Depends(get_account_email_service)):
    account_email.reset_password(str(payload.email), payload.code, payload.new_password)
    return {"message": "Contraseña actualizada correctamente."}


@router.get("/me", response_model=UserResponse)
def me(user=Depends(current_user)):
    return current_user_controller(user)


@router.patch("/me", response_model=UserResponse)
def update_me(payload: ProfileUpdateRequest, user=Depends(current_user), users: UserRepository = Depends(get_user_repository)):
    return update_profile_controller(users, user, payload)


@router.get("/me/academic-profile", response_model=AcademicProfileResponse | None)
def get_my_academic_profile(user=Depends(student)):
    return get_academic_profile(user)


@router.put("/me/academic-profile", response_model=AcademicProfileResponse)
def update_my_academic_profile(payload: AcademicProfileInput, user=Depends(student), users: UserRepository = Depends(get_user_repository)):
    return save_academic_profile(users, user, payload)


@router.post("/me/profile-photo", response_model=UserResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    user=Depends(current_user),
    users: UserRepository = Depends(get_user_repository),
    storage: VercelBlobStorage = Depends(get_blob_storage),
):
    return await ProfilePhotoService(users, storage).upload(user, file)


@router.get("/me/profile-photo")
async def get_profile_photo(
    user=Depends(current_user),
    storage: VercelBlobStorage = Depends(get_blob_storage),
):
    result, photo = await ProfilePhotoService(None, storage).get(user)
    return Response(
        content=result.content,
        media_type=photo["content_type"],
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "ETag": photo.get("etag", ""),
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/me/profile-photo", response_model=UserResponse)
async def delete_profile_photo(
    user=Depends(current_user),
    users: UserRepository = Depends(get_user_repository),
    storage: VercelBlobStorage = Depends(get_blob_storage),
):
    return await ProfilePhotoService(users, storage).delete(user)
