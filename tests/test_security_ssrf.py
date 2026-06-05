"""SSRF 防护纯函数测试。"""
from __future__ import annotations

import socket
import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.security import validate_public_http_url

# 固定公网 IP，用于 mock DNS 解析，避免真实网络请求
MOCK_PUBLIC_IP = "93.184.216.34"
MOCK_DNS_RESULT = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (MOCK_PUBLIC_IP, 0))]


class ValidatePublicHttpUrlTest(TestCase):
    def test_rejects_localhost(self) -> None:
        """拒绝 localhost 地址。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://localhost:8080/test")
        self.assertIn("localhost", str(ctx.exception))

    def test_rejects_localhost_no_port(self) -> None:
        """拒绝无端口的 localhost。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://localhost/test")
        self.assertIn("localhost", str(ctx.exception))

    def test_rejects_127_0_0_1(self) -> None:
        """拒绝 127.0.0.1 环回地址。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://127.0.0.1:8080/test")
        self.assertIn("内网或保留地址", str(ctx.exception))

    def test_rejects_10_0_0_1(self) -> None:
        """拒绝 10.0.0.1 内网地址。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://10.0.0.1/test")
        self.assertIn("内网或保留地址", str(ctx.exception))

    def test_rejects_192_168_1_1(self) -> None:
        """拒绝 192.168.1.1 内网地址。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://192.168.1.1/test")
        self.assertIn("内网或保留地址", str(ctx.exception))

    def test_rejects_169_254_169_254(self) -> None:
        """拒绝 169.254.169.254 链路本地地址（AWS metadata）。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://169.254.169.254/latest/meta-data/")
        self.assertIn("内网或保留地址", str(ctx.exception))

    def test_rejects_file_scheme(self) -> None:
        """拒绝 file:// 协议。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("file:///etc/passwd")
        self.assertIn("只允许 http 或 https", str(ctx.exception))

    def test_rejects_ftp_scheme(self) -> None:
        """拒绝 ftp:// 协议。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("ftp://example.com/file")
        self.assertIn("只允许 http 或 https", str(ctx.exception))

    def test_rejects_no_scheme(self) -> None:
        """拒绝无 scheme 的 URL。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("example.com/test")
        self.assertIn("只允许 http 或 https", str(ctx.exception))

    def test_rejects_empty_url(self) -> None:
        """拒绝空 URL。"""
        with self.assertRaises(ValueError):
            validate_public_http_url("")

    def test_rejects_missing_hostname(self) -> None:
        """拒绝缺少 hostname 的 URL。"""
        with self.assertRaises(ValueError) as ctx:
            validate_public_http_url("http://")
        self.assertIn("缺少 hostname", str(ctx.exception))

    def test_rejects_invalid_port(self) -> None:
        """拒绝无效端口。"""
        with patch("socket.getaddrinfo", side_effect=socket.error("Port out of range 0-65535")):
            with self.assertRaises(ValueError) as ctx:
                validate_public_http_url("http://example.com:99999/test")
            self.assertIn("Port out of range", str(ctx.exception))

    def test_allows_https_example_com(self) -> None:
        """允许 https://example.com/path。"""
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = validate_public_http_url("https://example.com/path?query=1")
            self.assertEqual(result, "https://example.com/path?query=1")

    def test_allows_http_example_com(self) -> None:
        """允许 http://example.com/path。"""
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = validate_public_http_url("http://example.com/test")
            self.assertEqual(result, "http://example.com/test")

    def test_allows_valid_port(self) -> None:
        """允许有效端口。"""
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = validate_public_http_url("https://example.com:443/test")
            self.assertEqual(result, "https://example.com:443/test")

    def test_strips_whitespace(self) -> None:
        """去除 URL 前后空格。"""
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = validate_public_http_url("  https://example.com/test  ")
            self.assertEqual(result, "https://example.com/test")


class EnsurePublicHttpUrlTest(TestCase):
    def test_strips_trailing_slash(self) -> None:
        """去除末尾斜杠。"""
        from angemedia_gateway.security import ensure_public_http_url
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = ensure_public_http_url("https://example.com/v1/")
            self.assertEqual(result, "https://example.com/v1")

    def test_preserves_path_without_slash(self) -> None:
        """保留无末尾斜杠的路径。"""
        from angemedia_gateway.security import ensure_public_http_url
        with patch("socket.getaddrinfo", return_value=MOCK_DNS_RESULT):
            result = ensure_public_http_url("https://example.com/v1")
            self.assertEqual(result, "https://example.com/v1")
