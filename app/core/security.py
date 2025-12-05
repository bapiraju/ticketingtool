from typing import Optional, Tuple
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

_bearer = HTTPBearer()


def _try_decode_with_secret(token: str, secret: str, algorithm: str) -> Tuple[bool, Optional[dict]]:
    """Attempt to decode token with given secret.
    
    Returns: (success, payload_or_error)
    """
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        return True, payload
    except ExpiredSignatureError:
        return False, {"_error": "expired"}
    except InvalidTokenError:
        return False, None


def _decode_token(token: str) -> Optional[dict]:
    """Decode token trying admin secret first, then user secret.
    
    Returns payload dict with '_verified_with' key, or None if all attempts fail.
    Returns {'_error': 'expired'} if token expired.
    """
    # Try admin secret first
    success, result = _try_decode_with_secret(token, settings.admin_jwt_secret, settings.jwt_algorithm)
    if success:
        result["_verified_with"] = "admin"
        return result
    if result and result.get("_error") == "expired":
        return result
    
    # Try user secret
    success, result = _try_decode_with_secret(token, settings.user_jwt_secret, settings.jwt_algorithm)
    if success:
        result["_verified_with"] = "user"
        return result
    if result and result.get("_error") == "expired":
        return result
    
    return None


def require_role(required: str):
    def _dependency(credentials: HTTPAuthorizationCredentials = Depends(_bearer)):
        token = credentials.credentials
        payload = _decode_token(token)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        if payload.get("_error") == "expired":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        role = payload.get("role") or payload.get("_verified_with")
        # allow admin to satisfy user requirement
        if required == "user" and role in ("user", "admin"):
            return payload
        if required == "admin" and role == "admin":
            return payload
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

    return _dependency
