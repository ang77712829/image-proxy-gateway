from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.providers.errors import ProviderProtocolError  # noqa: E402
from angemedia_gateway.providers.parsers import first_string_field, parse_size, require_mapping  # noqa: E402


class ProviderParsersTest(unittest.TestCase):
    def test_parse_size(self) -> None:
        self.assertEqual(parse_size("1024x768"), (1024, 768))

    def test_parse_size_rejects_invalid_text(self) -> None:
        with self.assertRaises(HTTPException):
            parse_size("1024")

    def test_parse_size_rejects_non_positive(self) -> None:
        with self.assertRaises(HTTPException):
            parse_size("0x768")

    def test_require_mapping(self) -> None:
        self.assertEqual(require_mapping({"ok": True}, provider="test", operation="parse"), {"ok": True})

    def test_require_mapping_rejects_non_object(self) -> None:
        with self.assertRaises(ProviderProtocolError):
            require_mapping([], provider="test", operation="parse")

    def test_first_string_field(self) -> None:
        self.assertEqual(first_string_field({"a": "", "b": "value"}, "a", "b"), "value")
        self.assertIsNone(first_string_field({"a": 1}, "a"))


if __name__ == "__main__":
    unittest.main()
