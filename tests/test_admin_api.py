from __future__ import annotations

import os
import sys
import tempfile
import unittest
import uuid
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


class AdminApiWriteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.created_provider_ids: list[str] = []
        self.login_admin()

    def tearDown(self) -> None:
        for provider_id in self.created_provider_ids:
            self.client.delete(f"/v1/admin/providers/{provider_id}")
        self.client.post(
            "/v1/admin/config",
            json={
                "settings": {
                    "GATEWAY_API_KEY": "",
                    "PUBLIC_BASE_URL": "http://testserver",
                    "OPENAI_IMAGE_API_KEY": "",
                }
            },
        )

    def login_admin(self) -> None:
        response = self.client.post(
            "/v1/admin/login",
            json={"username": "admin", "password": "admin123456"},
        )
        self.assertEqual(response.status_code, 200, response.text)

    def unique_provider_id(self, prefix: str = "phase-12b") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:10]}"

    def test_admin_config_rejects_invalid_values(self) -> None:
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

    def test_admin_config_save_persists_and_masks_secret(self) -> None:
        secret = "sk-phase-12b-secret-value-123456"
        public_url = "https://example.com/angemedia"

        response = self.client.post(
            "/v1/admin/config",
            json={
                "settings": {
                    "PUBLIC_BASE_URL": public_url,
                    "OPENAI_IMAGE_API_KEY": secret,
                }
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        settings = response.json()["settings"]
        self.assertEqual(settings["PUBLIC_BASE_URL"], public_url)
        self.assertIn("*", settings["OPENAI_IMAGE_API_KEY"])
        self.assertNotEqual(settings["OPENAI_IMAGE_API_KEY"], secret)
        self.assertNotIn(secret, response.text)

        config = self.client.get("/v1/admin/config")
        self.assertEqual(config.status_code, 200, config.text)
        saved_settings = config.json()["settings"]
        self.assertEqual(saved_settings["PUBLIC_BASE_URL"], public_url)
        self.assertIn("*", saved_settings["OPENAI_IMAGE_API_KEY"])
        self.assertNotIn(secret, config.text)

    def test_gateway_key_generation_modes_and_saved_key_auth(self) -> None:
        unsaved = self.client.post("/v1/admin/gateway-key", json={"save": False})
        self.assertEqual(unsaved.status_code, 200, unsaved.text)
        unsaved_data = unsaved.json()
        self.assertFalse(unsaved_data["saved"])
        self.assertRegex(unsaved_data["key"], r"^am-[a-f0-9]{32}$")

        saved = self.client.post("/v1/admin/gateway-key", json={"save": True})
        self.assertEqual(saved.status_code, 200, saved.text)
        saved_data = saved.json()
        self.assertTrue(saved_data["saved"])
        self.assertIn("****", saved_data["key_preview"])
        self.assertNotIn("key", saved_data)

        unauthenticated = TestClient(app)
        locked = unauthenticated.get("/v1/models")
        self.assertEqual(locked.status_code, 401, locked.text)

        known_key = unsaved_data["key"]
        configured = self.client.post(
            "/v1/admin/config",
            json={"settings": {"GATEWAY_API_KEY": known_key}},
        )
        self.assertEqual(configured.status_code, 200, configured.text)

        authorized = TestClient(app).get("/v1/models", headers={"Authorization": f"Bearer {known_key}"})
        self.assertEqual(authorized.status_code, 200, authorized.text)

    def test_provider_save_validation_errors(self) -> None:
        missing_required = self.client.post(
            "/v1/admin/providers",
            json={"id": self.unique_provider_id("missing"), "name": "Missing Required"},
        )
        self.assertEqual(missing_required.status_code, 400, missing_required.text)
        self.assertEqual(missing_required.json()["detail"], "base_url 和 default_model 必填")

        private_url = self.client.post(
            "/v1/admin/providers",
            json={
                "id": self.unique_provider_id("private"),
                "name": "Private URL",
                "base_url": "http://localhost:9890/v1",
                "default_model": "private-model",
            },
        )
        self.assertEqual(private_url.status_code, 400, private_url.text)
        self.assertIn("localhost", private_url.json()["detail"])

    def test_custom_provider_create_masks_key_toggle_and_delete(self) -> None:
        provider_id = self.unique_provider_id()
        self.created_provider_ids.append(provider_id)
        secret = "sk-custom-provider-secret-123456"

        created = self.client.post(
            "/v1/admin/providers",
            json={
                "id": provider_id,
                "name": "Phase 12B Provider",
                "provider_type": "openai_image",
                "base_url": "https://example.com/v1",
                "api_key": secret,
                "default_model": "test-image-model",
                "enabled": True,
                "sort_order": 123,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        created_data = created.json()["data"]
        self.assertEqual(created_data["id"], provider_id)
        self.assertNotEqual(created_data["api_key"], secret)
        self.assertIn("*", created_data["api_key"])

        providers = self.client.get("/v1/admin/providers")
        self.assertEqual(providers.status_code, 200, providers.text)
        indexed = {item["id"]: item for item in providers.json()["data"]}
        self.assertIn(provider_id, indexed)
        self.assertNotEqual(indexed[provider_id]["api_key"], secret)
        self.assertIn("*", indexed[provider_id]["api_key"])

        disabled = self.client.post(f"/v1/admin/providers/{provider_id}/enabled", json={"enabled": False})
        self.assertEqual(disabled.status_code, 200, disabled.text)
        self.assertFalse(disabled.json()["data"]["enabled"])

        enabled = self.client.post(f"/v1/admin/providers/{provider_id}/enabled", json={"enabled": True})
        self.assertEqual(enabled.status_code, 200, enabled.text)
        self.assertTrue(enabled.json()["data"]["enabled"])

        deleted = self.client.delete(f"/v1/admin/providers/{provider_id}")
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertTrue(deleted.json()["ok"])
        self.created_provider_ids.remove(provider_id)

    def test_provider_delete_missing_and_builtin_sort_errors(self) -> None:
        missing = self.client.delete(f"/v1/admin/providers/{self.unique_provider_id('missing')}")
        self.assertEqual(missing.status_code, 404, missing.text)
        self.assertEqual(missing.json()["detail"], "自定义渠道不存在")

        built_in_sort = self.client.post("/v1/admin/providers/siliconflow/sort", json={"sort_order": 99})
        self.assertEqual(built_in_sort.status_code, 400, built_in_sort.text)
        self.assertEqual(built_in_sort.json()["detail"], "内置渠道排序固定；默认链路顺序由网关维护")


if __name__ == "__main__":
    unittest.main()
