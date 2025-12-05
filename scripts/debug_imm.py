import os
import tempfile
from fastapi.testclient import TestClient

tmpdir = tempfile.TemporaryDirectory()
db_path = os.path.join(tmpdir.name, "settings_test.db")
os.environ["SETTINGS_USE_DB"] = "1"
os.environ["SETTINGS_DB_PATH"] = db_path

from app.core.config import settings
from app.core.token import create_token
from app.main import app

print("before immutable_keys:", settings.immutable_keys)
settings.immutable_keys = ["TEST_IMM"]
print("after immutable_keys:", settings.immutable_keys)

client = TestClient(app)
admin_token = create_token(role="admin", subject="debug-admin", expires_seconds=600)
headers_admin = {"Authorization": f"Bearer {admin_token}"}

r = client.put("/admin/settings/TEST_IMM", headers=headers_admin, json={"value":"orig"})
print("status:", r.status_code)
try:
    print("body:", r.json())
except Exception:
    print("text:", r.text)
