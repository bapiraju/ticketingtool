import sys
import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from app.core.config import settings


def try_decode(token: str, secret: str, alg: str):
    try:
        payload = jwt.decode(token, secret, algorithms=[alg])
        return True, payload
    except ExpiredSignatureError:
        return False, "expired"
    except InvalidTokenError as e:
        return False, str(e)


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_token_verify.py <token>")
        sys.exit(2)
    token = sys.argv[1]
    print("Using settings:")
    print("  ADMIN_JWT_SECRET:", repr(settings.admin_jwt_secret))
    print("  USER_JWT_SECRET:", repr(settings.user_jwt_secret))
    print("  JWT_ALGORITHM:", settings.jwt_algorithm)

    ok, res = try_decode(token, settings.admin_jwt_secret, settings.jwt_algorithm)
    print("\nTried admin secret:")
    if ok:
        print("  OK — payload:", res)
    else:
        print("  Failed —", res)

    ok, res = try_decode(token, settings.user_jwt_secret, settings.jwt_algorithm)
    print("\nTried user secret:")
    if ok:
        print("  OK — payload:", res)
    else:
        print("  Failed —", res)


if __name__ == "__main__":
    main()
