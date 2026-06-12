from __future__ import annotations

import sys
import unittest
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.providers.errors import ProviderProtocolError, ProviderTimeout, ProviderUnavailable  # noqa: E402
from angemedia_gateway.providers.http import normalize_httpx_error, provider_timeout, safe_json_response  # noqa: E402


class ProviderHttpTest(unittest.TestCase):
    def test_provider_timeout_uses_configurable_float(self) -> None:
        timeout = provider_timeout(12.5)
        self.assertIsInstance(timeout, httpx.Timeout)
        self.assertEqual(timeout.connect, 12.5)

    def test_safe_json_response_returns_json(self) -> None:
        response = httpx.Response(200, json={"ok": True})
        self.assertEqual(safe_json_response(response, provider="test", operation="generate"), {"ok": True})

    def test_safe_json_response_does_not_leak_raw_body(self) -> None:
        marker = "RAW_BODY_SHOULD_NOT_LEAK"
        response = httpx.Response(200, content=marker.encode("utf-8"))
        with self.assertRaises(ProviderProtocolError) as ctx:
            safe_json_response(response, provider="test", operation="generate")
        self.assertNotIn(marker, str(ctx.exception))
        self.assertIn("invalid JSON", str(ctx.exception))
        self.assertEqual(ctx.exception.status_code, 200)

    def test_normalize_timeout(self) -> None:
        error = normalize_httpx_error(httpx.ReadTimeout("boom"), provider="test", operation="generate")
        self.assertIsInstance(error, ProviderTimeout)
        self.assertTrue(error.retryable)
        self.assertNotIn("boom", str(error))

    def test_normalize_network_error(self) -> None:
        error = normalize_httpx_error(httpx.ConnectError("secret host body"), provider="test", operation="generate")
        self.assertIsInstance(error, ProviderUnavailable)
        self.assertTrue(error.retryable)
        self.assertEqual(error.error_category, "network")
        self.assertNotIn("secret host body", str(error))


if __name__ == "__main__":
    unittest.main()
