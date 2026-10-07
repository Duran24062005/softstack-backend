import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}



def _parse_cors_origins() -> list[str]:
    raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    return [origin.strip().rstrip("/") for origin in raw_origins.split(",") if origin.strip()]


def _parse_csv(name: str) -> list[str]:
    return [item.strip().lower() for item in os.getenv(name, "").split(",") if item.strip()]


app_config = {
    "APP_NAME": os.getenv("APP_NAME", "SoftStack"),
    "VERSION": os.getenv("APP_VERSION", "1.0.0"),
    "DESCRIPTION": "API for managing and storing data in the SoftStack app",
    "HOST": os.getenv("HOST", "0.0.0.0"),
    "PORT": _env_int("PORT", 8000),
    "CORS_ORIGINS": _parse_cors_origins(),
}

database_config = {
    "MONGODB_URI": os.getenv("MONGODB_URI", "mongodb://localhost:27017"),
    "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "softstack"),
    "MONGODB_SERVER_SELECTION_TIMEOUT_MS": _env_int("MONGODB_SERVER_SELECTION_TIMEOUT_MS", 2_000),
    "MONGODB_MAX_POOL_SIZE": _env_int("MONGODB_MAX_POOL_SIZE", 100),
    "MONGODB_MIN_POOL_SIZE": _env_int("MONGODB_MIN_POOL_SIZE", 0),
}

security_config = {
    "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "change-me-in-production-use-a-32-byte-secret"),
    "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
    "ACCESS_TOKEN_EXPIRE_MINUTES": _env_int("ACCESS_TOKEN_EXPIRE_MINUTES", 15),
    "REFRESH_TOKEN_EXPIRE_DAYS": _env_int("REFRESH_TOKEN_EXPIRE_DAYS", 30),
    "PASSWORD_HASH_SCHEME": os.getenv("PASSWORD_HASH_SCHEME", "argon2id"),
    "ADMIN_EMAILS": _parse_csv("ADMIN_EMAILS"),
}

email_config = {
    "SERVICE_URL": os.getenv("EMAIL_SERVICE_URL", "https://email-python-fast-api.vercel.app").rstrip("/"),
    "REQUEST_TIMEOUT_SECONDS": _env_int("EMAIL_REQUEST_TIMEOUT_SECONDS", 10),
    "FRONTEND_URL": os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/"),
    "VERIFICATION_EXPIRE_MINUTES": _env_int("EMAIL_VERIFICATION_EXPIRE_MINUTES", 1_440),
    "RESET_CODE_EXPIRE_MINUTES": _env_int("PASSWORD_RESET_CODE_EXPIRE_MINUTES", 10),
    "RESET_MAX_ATTEMPTS": _env_int("PASSWORD_RESET_MAX_ATTEMPTS", 5),
}

cookie_config = {
    "ACCESS_COOKIE_NAME": os.getenv("ACCESS_COOKIE_NAME", "softstack_access"),
    "REFRESH_COOKIE_NAME": os.getenv("REFRESH_COOKIE_NAME", "softstack_refresh"),
    "SECURE": _env_bool("COOKIE_SECURE", False),
    "SAMESITE": os.getenv("COOKIE_SAMESITE", "lax"),
    "DOMAIN": os.getenv("COOKIE_DOMAIN") or None,
}

blob_config = {
    "STORE_ID": os.getenv("BLOB_STORE_ID", ""),
    "READ_WRITE_TOKEN": os.getenv("BLOB_READ_WRITE_TOKEN", ""),
    "ACCESS": "private",
    "MAX_FILE_SIZE_BYTES": 3_000_000,
    "ALLOWED_CONTENT_TYPES": {"image/jpeg", "image/png", "image/webp"},
}


content_blob_config = {
    "STORE_ID": os.getenv("CONTENT_BLOB_STORE_ID", ""),
    "READ_WRITE_TOKEN": os.getenv("CONTENT_BLOB_READ_WRITE_TOKEN", ""),
    "ACCESS": "public",
    "PREFIX": "content-media/",
    "PUBLIC_HOST": os.getenv("CONTENT_BLOB_PUBLIC_HOST", ""),
    "MAX_IMAGE_SIZE_BYTES": _env_int("CONTENT_BLOB_MAX_IMAGE_SIZE_BYTES", 10_000_000),
    "MAX_VIDEO_SIZE_BYTES": _env_int("CONTENT_BLOB_MAX_VIDEO_SIZE_BYTES", 100_000_000),
    "ALLOWED_IMAGE_CONTENT_TYPES": {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/avif",
    },
    "ALLOWED_VIDEO_CONTENT_TYPES": {
        "video/mp4",
        "video/webm",
        "video/quicktime",
    },
    "IMPORT_TIMEOUT_SECONDS": _env_int("CONTENT_BLOB_IMPORT_TIMEOUT_SECONDS", 10),
    "ORPHAN_RETENTION_HOURS": _env_int("CONTENT_BLOB_ORPHAN_RETENTION_HOURS", 24),
}


cron_config = {
    "SECRET": os.getenv("CRON_SECRET", ""),
}
