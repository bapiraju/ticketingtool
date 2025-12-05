import os
import json
from fastapi.testclient import TestClient


def setup_module(module):
    # Ensure tests use DB-backed settings isolated in tmp file location
    # The test that calls this will override SETTINGS_DB_PATH
    os.environ["SETTINGS_USE_DB"] = "1"


def test_admin_and_user_permissions(tmp_path):
    # Use a temporary sqlite file for settings storage
    db_path = tmp_path / "settings_test.db"
    os.environ["SETTINGS_DB_PATH"] = str(db_path)

    # Import after env var set so stores pick up DB mode
    from app.core.token import create_token
    from app.core.config import settings, update_and_reload
    from app.main import app

    client = TestClient(app)

    # No auth -> 401
    r = client.get("/admin/settings")
    assert r.status_code == 401

    # Create tokens
    admin_token = create_token(role="admin", subject="test-admin", expires_seconds=600)
    user_token = create_token(role="user", subject="test-user", expires_seconds=600)

    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_user = {"Authorization": f"Bearer {user_token}"}

    # Admin can read settings
    r = client.get("/admin/settings", headers=headers_admin)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)

    # User can also read
    r = client.get("/admin/settings", headers=headers_user)
    assert r.status_code == 200

    # Admin can create multiple keys (bulk PUT)
    payload = {"TEST_NEW1": "v1", "TEST_NEW2": "v2"}
    r = client.put("/admin/settings", headers=headers_admin, json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    assert "added" in body

    # Verify keys present
    r = client.get("/admin/settings/TEST_NEW1", headers=headers_admin)
    assert r.status_code == 200
    assert r.json()["TEST_NEW1"] == "v1"

    # Admin can update existing keys (bulk POST)
    up = {"TEST_NEW1": "v1b", "TEST_NEW2": "v2b"}
    r = client.post("/admin/settings", headers=headers_admin, json=up)
    assert r.status_code == 200
    assert r.json().get("updated")

    # User cannot write (should be forbidden)
    r = client.put("/admin/settings", headers=headers_user, json={"X":"1"})
    assert r.status_code in (401, 403)


def test_immutable_blocking(tmp_path):
    db_path = tmp_path / "settings_test.db"
    os.environ["SETTINGS_DB_PATH"] = str(db_path)
    os.environ["SETTINGS_USE_DB"] = "1"

    from app.core.token import create_token
    from app.core.config import settings
    from app.main import app

    client = TestClient(app)
    admin_token = create_token(role="admin", subject="test-admin", expires_seconds=600)
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Mark TEST_IMM as immutable in-memory
    settings.immutable_keys = ["TEST_IMM"]

    # Create TEST_IMM key first
    r = client.put("/admin/settings/TEST_IMM", headers=headers_admin, json={"value": "orig"})
    # Creation should fail because immutable prevents creation/modification
    assert r.status_code == 403
