from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("IMAGE_PROXY_STATE_DIR", tempfile.mkdtemp(prefix="angemedia-test-"))
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("AUTO_DOWNLOAD_GENERATED", "false")
os.environ.setdefault("SILICONFLOW_API_KEY", "sf-test-secret-value")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "admin123456")

from fastapi.testclient import TestClient  # noqa: E402

from angemedia_gateway.server import app  # noqa: E402


class GatewaySmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def login_admin(self) -> None:
        response = self.client.post(
            "/v1/admin/login",
            json={"username": "admin", "password": "admin123456"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def test_public_routes_are_available(self) -> None:
        for path in ["/", "/admin", "/api-docs", "/health", "/v1/models"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200, response.text)

    def test_admin_config_metadata_and_secret_masking(self) -> None:
        self.login_admin()

        metadata = self.client.get("/v1/admin/config-metadata")
        self.assertEqual(metadata.status_code, 200, metadata.text)
        self.assertGreaterEqual(len(metadata.json().get("groups", [])), 5)

        config = self.client.get("/v1/admin/config")
        self.assertEqual(config.status_code, 200, config.text)
        settings = config.json()["settings"]
        self.assertIn("SILICONFLOW_API_KEY", settings)
        self.assertNotEqual(settings["SILICONFLOW_API_KEY"], "sf-test-secret-value")
        self.assertIn("*", settings["SILICONFLOW_API_KEY"])

    def test_admin_config_rejects_invalid_values(self) -> None:
        self.login_admin()
        invalid_payloads = [
            {"AUTO_DOWNLOAD_GENERATED": "not-a-bool"},
            {"MEDIA_DOWNLOAD_MAX_BYTES": "not-an-int"},
            {"PUBLIC_BASE_URL": "ftp://example.test"},
        ]

        for settings in invalid_payloads:
            with self.subTest(settings=settings):
                response = self.client.post("/v1/admin/config", json={"settings": settings})
                self.assertEqual(response.status_code, 400, response.text)
                self.assertIn("detail", response.json())

    def test_health_returns_ok(self) -> None:
        """/health 精确等于 {"status": "ok"}。"""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_health_no_forbidden_fields(self) -> None:
        """/health 不包含敏感字段。"""
        response = self.client.get("/health")
        body = response.json()
        forbidden = [
            "name", "version", "auth_enabled",
            "siliconflow", "modelscope", "pollinations",
            "openai_image", "agnes_image", "agnes_video",
            "storage_ready", "assistant", "models",
            "configured", "enabled",
        ]
        for field in forbidden:
            self.assertNotIn(field, body, f"/health 不应包含 {field}")


if __name__ == "__main__":
    unittest.main()
