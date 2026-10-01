from fastapi import Response

from app.config.config import cookie_config, security_config


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    common = {
        "httponly": True,
        "secure": cookie_config["SECURE"],
        "samesite": cookie_config["SAMESITE"],
        "domain": cookie_config["DOMAIN"],
        "path": "/",
    }
    response.set_cookie(
        cookie_config["ACCESS_COOKIE_NAME"],
        access_token,
        max_age=security_config["ACCESS_TOKEN_EXPIRE_MINUTES"] * 60,
        **common,
    )
    response.set_cookie(
        cookie_config["REFRESH_COOKIE_NAME"],
        refresh_token,
        max_age=security_config["REFRESH_TOKEN_EXPIRE_DAYS"] * 24 * 60 * 60,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    common = {
        "secure": cookie_config["SECURE"],
        "samesite": cookie_config["SAMESITE"],
        "domain": cookie_config["DOMAIN"],
        "path": "/",
    }
    response.delete_cookie(cookie_config["ACCESS_COOKIE_NAME"], **common)
    response.delete_cookie(cookie_config["REFRESH_COOKIE_NAME"], **common)
