from typing import Optional
import time
import jwt

from app.core.config import settings


def create_token(role: str = "user", subject: Optional[str] = None, expires_seconds: Optional[int] = 3600) -> str:
    now = int(time.time())
    payload = {
        "iat": now,
        "role": role,
    }
    if subject:
        payload["sub"] = subject
    if expires_seconds:
        payload["exp"] = now + int(expires_seconds)

    # Choose secret based on role
    if role == "admin":
        secret = settings.admin_jwt_secret
    else:
        secret = settings.user_jwt_secret

    token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    return token
