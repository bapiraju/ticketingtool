from app.core.store import get_store
from app.core.config import settings
import os


def main():
    print("Environment variables (sample):")
    for k in ("ADMIN_JWT_SECRET", "USER_JWT_SECRET", "JWT_ALGORITHM", "SETTINGS_USE_DB"):
        print(f"  {k} = {repr(os.getenv(k))}")

    print("\nsettings object snapshot:")
    try:
        print(settings.model_dump(by_alias=True))
    except Exception:
        try:
            print({k: getattr(settings, k) for k in dir(settings) if k.isupper()})
        except Exception:
            print("  <unable to dump settings>")

    print("\nStore read_all():")
    store = get_store()
    try:
        vals = store.read_all()
        for k, v in vals.items():
            print(f"  {k} = {repr(v)}")
    except Exception as e:
        print("  Failed to read store:", e)


if __name__ == "__main__":
    main()
