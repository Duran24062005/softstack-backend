from fastapi import Depends

from app.core.exception import AuthorizationError
from app.routes.dependencies import current_user


def require_roles(*roles: str):
    def dependency(user=Depends(current_user)):
        if user.get("role") not in roles:
            raise AuthorizationError
        return user
    return dependency
