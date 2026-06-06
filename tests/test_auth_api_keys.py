"""Gateway API Key 接入普通 API 和 Admin 边界测试。"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "admin123456")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("AUTO_DOWNLOAD_GENERATED", "false")
os.environ.setdefault("SILICONFLOW_API_KEY", "sf-test-secret-value")

from fastapi.testclient import TestClient  # noqa: E402

import angemedia_gateway.config as C  # noqa: E402
from angemedia_gateway.server import app  # noqa: E402
from angemedia_gateway.state import (  # noqa: E402
    create_gateway_api_key,
    ensure_default_admin_user,
    init_db,
    revoke_gateway_api_key,
    update_gateway_api_key,
)


class GatewayApiKeyAuthTest(unittest.TestCase):
    """普通 /v1/* 与 /v1/admin/* 的 Gateway API Key 鉴权边界。"""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.mkdtemp(prefix="auth-api-key-test-")
        self._db_path = Path(self._tmp_dir) / "test.db"
        self._output_dir = Path(self._tmp_dir) / "output"
        self._upload_dir = Path(self._tmp_dir) / "upload"
        self._output_dir.mkdir()
        self._upload_dir.mkdir()

        self._orig_db = C.DB_FILE
        self._orig_output = C.OUTPUT_DIR
        self._orig_upload = C.UPLOAD_DIR
        self._orig_base_url = C.PUBLIC_BASE_URL
        self._orig_gateway_key = C.GATEWAY_API_KEY
        self._orig_admin_user = os.environ.get("ADMIN_USERNAME")
        self._orig_admin_pass = os.environ.get("ADMIN_DEFAULT_PASSWORD")

        C.DB_FILE = self._db_path
        C.OUTPUT_DIR = self._output_dir
        C.UPLOAD_DIR = self._upload_dir
        C.PUBLIC_BASE_URL = "http://testserver"
        C.GATEWAY_API_KEY = ""
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123456"
        init_db()
        ensure_default_admin_user()
        self.client = TestClient(app)

    def tearDown(self) -> None:
        C.DB_FILE = self._orig_db
        C.OUTPUT_DIR = self._orig_output
        C.UPLOAD_DIR = self._orig_upload
        C.PUBLIC_BASE_URL = self._orig_base_url
        C.GATEWAY_API_KEY = self._orig_gateway_key
        if self._orig_admin_user is None:
            os.environ.pop("ADMIN_USERNAME", None)
        else:
            os.environ["ADMIN_USERNAME"] = self._orig_admin_user
        if self._orig_admin_pass is None:
            os.environ.pop("ADMIN_DEFAULT_PASSWORD", None)
        else:
            os.environ["ADMIN_DEFAULT_PASSWORD"] = self._orig_admin_pass
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def login_admin(self) -> TestClient:
        client = TestClient(app)
        response = client.post(
            "/v1/admin/login",
            json={"username": "admin", "password": "admin123456"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        return client

    def create_db_key(self, *, enabled: bool = True, revoked: bool = False) -> dict:
        item = create_gateway_api_key(name="auth-test")
        if not enabled:
            updated = update_gateway_api_key(item["id"], enabled=False)
            self.assertIsNotNone(updated)
        if revoked:
            self.assertTrue(revoke_gateway_api_key(item["id"]))
        return item

    def assert_no_secret_leak(self, response_text: str, secret: str) -> None:
        self.assertNotIn(secret, response_text)
        self.assertNotIn("key_hash", response_text)

    # ── 普通 /v1/* 鉴权 ────────────────────────────────

    def test_models_open_when_no_legacy_key_and_no_db_records(self) -> None:
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 200, response.text)

    def test_models_require_auth_when_db_key_record_exists(self) -> None:
        self.create_db_key()
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 401, response.text)

    def test_db_key_bearer_can_access_models(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get("/v1/models", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 200, response.text)

    def test_db_key_x_api_key_can_access_models(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get("/v1/models", headers={"X-API-Key": key})
        self.assertEqual(response.status_code, 200, response.text)

    def test_disabled_db_key_cannot_access_models(self) -> None:
        key = self.create_db_key(enabled=False)["key"]
        response = self.client.get("/v1/models", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 401, response.text)

    def test_revoked_db_key_cannot_access_models(self) -> None:
        key = self.create_db_key(revoked=True)["key"]
        response = self.client.get("/v1/models", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 401, response.text)

    def test_wrong_key_cannot_access_models_when_auth_enabled(self) -> None:
        self.create_db_key()
        response = self.client.get("/v1/models", headers={"Authorization": "Bearer am-wrong-key"})
        self.assertEqual(response.status_code, 401, response.text)

    def test_legacy_bearer_key_can_access_models(self) -> None:
        C.GATEWAY_API_KEY = "am-legacy-auth-test"
        response = self.client.get("/v1/models", headers={"Authorization": "Bearer am-legacy-auth-test"})
        self.assertEqual(response.status_code, 200, response.text)

    def test_legacy_x_api_key_can_access_models(self) -> None:
        C.GATEWAY_API_KEY = "am-legacy-auth-test"
        response = self.client.get("/v1/models", headers={"X-API-Key": "am-legacy-auth-test"})
        self.assertEqual(response.status_code, 200, response.text)

    def test_conflicting_bearer_and_x_api_key_return_401(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get(
            "/v1/models",
            headers={"Authorization": f"Bearer {key}", "X-API-Key": "am-different"},
        )
        self.assertEqual(response.status_code, 401, response.text)

    def test_matching_bearer_and_x_api_key_can_access_models(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get(
            "/v1/models",
            headers={"Authorization": f"Bearer {key}", "X-API-Key": key},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_revoked_db_key_record_keeps_models_auth_enabled(self) -> None:
        self.create_db_key(revoked=True)
        response = self.client.get("/v1/models")
        self.assertEqual(response.status_code, 401, response.text)

    # ── Admin API 权限边界 ─────────────────────────────

    def test_admin_session_can_access_gateway_keys(self) -> None:
        client = self.login_admin()
        response = client.get("/v1/admin/gateway-keys")
        self.assertEqual(response.status_code, 200, response.text)

    def test_db_gateway_key_cannot_access_admin_gateway_keys(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get("/v1/admin/gateway-keys", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 403, response.text)
        self.assert_no_secret_leak(response.text, key)

    def test_legacy_gateway_key_cannot_access_admin_gateway_keys(self) -> None:
        C.GATEWAY_API_KEY = "am-legacy-admin-denied"
        response = self.client.get(
            "/v1/admin/gateway-keys",
            headers={"Authorization": "Bearer am-legacy-admin-denied"},
        )
        self.assertEqual(response.status_code, 403, response.text)
        self.assert_no_secret_leak(response.text, "am-legacy-admin-denied")

    def test_admin_gateway_keys_without_session_or_key_returns_401(self) -> None:
        response = self.client.get("/v1/admin/gateway-keys")
        self.assertEqual(response.status_code, 401, response.text)

    def test_admin_session_wins_when_gateway_key_header_is_present(self) -> None:
        key = self.create_db_key()["key"]
        client = self.login_admin()
        response = client.get("/v1/admin/gateway-keys", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("key_hash", response.text)

    def test_admin_session_status_does_not_accept_db_gateway_key(self) -> None:
        key = self.create_db_key()["key"]
        response = self.client.get("/v1/admin/session", headers={"Authorization": f"Bearer {key}"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"authenticated": False})
        self.assert_no_secret_leak(response.text, key)

    def test_admin_session_status_does_not_accept_legacy_gateway_key(self) -> None:
        C.GATEWAY_API_KEY = "am-legacy-session-denied"
        response = self.client.get(
            "/v1/admin/session",
            headers={"Authorization": "Bearer am-legacy-session-denied"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"authenticated": False})
        self.assert_no_secret_leak(response.text, "am-legacy-session-denied")


if __name__ == "__main__":
    unittest.main()
