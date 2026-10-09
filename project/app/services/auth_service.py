"""JWT issuing/validation (bonus feature)."""
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.schemas.auth import TokenResponse

_bearer = HTTPBearer(auto_error=False)  # auto_error=False -> we control the 401 body


def authenticate(settings: Settings, username: str, password: str) -> bool:
    # constant-time comparison to avoid timing attacks
    return secrets.compare_digest(username, settings.admin_username) and secrets.compare_digest(
        password, settings.admin_password
    )


def create_token(settings: Settings, subject: str) -> TokenResponse:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    token = jwt.encode(
        {"sub": subject, "exp": expires}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    """Route dependency. No-op when AUTH_ENABLED=false."""
    settings: Settings = request.app.state.settings
    if not settings.auth_enabled:
        return "anonymous"
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(
            credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    return str(payload["sub"])
