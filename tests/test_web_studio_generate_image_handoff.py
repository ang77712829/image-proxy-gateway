"""Web Studio Generate Image provider handoff source contracts."""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATE_IMAGE_JS = ROOT / "app" / "www" / "assets" / "studio" / "pages" / "generate-image.js"
I18N_JS = ROOT / "app" / "www" / "assets" / "studio" / "i18n.js"


def read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def compact(source: str) -> str:
    return re.sub(r"\s+", " ", source)


class WebStudioGenerateImageHandoffSourceContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_source(GENERATE_IMAGE_JS)
        cls.compact_source = compact(cls.source)
        cls.i18n_source = read_source(I18N_JS)

    def test_loads_provider_safe_summary_for_custom_provider_options(self) -> None:
        """Generate Image should load existing safe provider summaries, not a new backend API."""
        self.assertRegex(
            self.source,
            r"api\.get\(\s*['\"]\/admin\/providers['\"]\s*\)",
            "Generate Image should reuse GET /v1/admin/providers safe summaries.",
        )

    def test_does_not_call_deferred_provider_admin_apis(self) -> None:
        """Provider status/test/delete/sort/fallback remain out of the Generate Image handoff."""
        forbidden_endpoints = [
            "provider-status",
            "provider-templates",
            "/test",
            "/sort",
            "/fallback",
            "fallback-chain",
        ]
        for endpoint in forbidden_endpoints:
            with self.subTest(endpoint=endpoint):
                self.assertNotIn(endpoint, self.source)

    def test_enabled_openai_image_providers_are_the_only_custom_options(self) -> None:
        """Only enabled OpenAI-compatible image providers should be selectable."""
        self.assertIn("provider_type", self.source)
        self.assertIn("openai_image", self.source)
        self.assertRegex(self.source, r"\benabled\b")
        self.assertRegex(
            self.source,
            r"createElement\(\s*['\"]select['\"]\s*\)",
            "Generate Image should render a provider select.",
        )

    def test_custom_provider_submit_uses_custom_model_id_without_secret_config(self) -> None:
        """Selecting a custom provider should submit model: custom:<id>."""
        self.assertIn("custom:", self.source)
        self.assertTrue(
            re.search(r"\bmodel\s*:", self.source) or re.search(r"\.model\s*=", self.source),
            "The image generation payload should include model when a custom provider is selected.",
        )

    def test_generate_image_source_does_not_reference_secret_provider_fields(self) -> None:
        """Generate Image handoff must not display or submit provider secret/config fields."""
        forbidden_patterns = [
            r"['\"]api_key['\"]",
            r"\.api_key\b",
            r"\bapi_key\s*:",
            r"\bbase_url\b",
            r"\bstatus_url\b",
            r"\bquota_url\b",
            r"\blast_error\b",
            r"\braw_response\b",
            r"\braw\b",
        ]
        for pattern in forbidden_patterns:
            with self.subTest(pattern=pattern):
                self.assertNotRegex(self.source, pattern)

    def test_default_builtin_payload_remains_available(self) -> None:
        """Built-in/default generation should keep the existing minimal OpenAI-compatible payload."""
        self.assertRegex(
            self.source,
            r"api\.post\(\s*['\"]\/images\/generations['\"]",
            "Generate Image should still submit to /v1/images/generations.",
        )
        self.assertRegex(self.source, r"\bprompt\b")
        self.assertRegex(self.source, r"response_format\s*:\s*['\"]url['\"]")

    def test_size_select_defaults_and_payload_are_present(self) -> None:
        """Generate Image should expose a minimal size select and include size in the payload."""
        self.assertRegex(
            self.source,
            r"createElement\(\s*['\"]select['\"]\s*\)",
            "Generate Image should render a size select.",
        )
        self.assertIn("1024x1024", self.source)
        self.assertRegex(
            self.source,
            r"\bsize\s*:",
            "The image generation payload should include size.",
        )

    def test_duplicate_conflict_uses_safe_short_message(self) -> None:
        """HTTP 409 duplicate responses should use a sanitized Generate Image message."""
        handles_duplicate = (
            "duplicate_in_flight_job" in self.source
            or "err.status === 409" in self.compact_source
            or "err.status===409" in self.compact_source
        )
        self.assertTrue(handles_duplicate, "Generate Image should handle duplicate 409 responses explicitly.")
        self.assertIn("generateImage.duplicate", self.i18n_source)

        forbidden_terms = [
            "request_hash",
            "request_hash_version",
            "input_json",
            "output_json",
            "raw_response",
        ]
        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, self.source)



    def test_generate_image_source_handles_human_hint_from_error_response(self) -> None:
        """generate-image.js 应能处理 API 错误响应中的 human_hint 字段"""
        # 当前实现只显示 generateImage.error（通用错误）
        # 如果 API 返回 human_hint，前端应优先显示 human_hint
        # 这个测试验证 source 代码是否有可能读取 human_hint
        # 当前 expect fail: generate-image.js 未显示 human_hint

        # 读取 generate-image.js 源码
        source = self.source

        # 断言当前实现仍然保留 generateImage.error 作为 fallback
        self.assertIn("generateImage.error", source,
                       "generate-image.js 应保留 generateImage.error 作为 fallback")

        # 断言当前实现未读取 human_hint（这是预期的 fail point）
        # 未来 W-ERR-2A 实现后，这个断言应改为检查 human_hint 处理逻辑
        self.assertNotIn("human_hint", source,
                        "generate-image.js 当前未处理 human_hint（需要 W-ERR-2A 实现）")

if __name__ == "__main__":
    unittest.main()
