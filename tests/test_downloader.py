"""Downloader atomic write and remote media fetch tests."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("AUTO_DOWNLOAD_GENERATED", "true")
os.environ.setdefault("SILICONFLOW_API_KEY", "sf-test-secret-value")
os.environ.setdefault("MEDIA_DOWNLOAD_MAX_BYTES", "10485760")

import angemedia_gateway.config as C
from angemedia_gateway.media import (
    download_remote_media,
    extension_from_response,
    stable_filename,
    try_download_remote_media,
)
from angemedia_gateway.state import (
    generation_metadata_by_filename,
    known_generated_local_paths,
)


class ExtensionFromResponseTest(unittest.TestCase):
    def test_png_content_type(self):
        ext = extension_from_response("http://example.com/file", "image/png", ".bin")
        self.assertEqual(ext, ".png")

    def test_jpeg_content_type(self):
        ext = extension_from_response("http://example.com/file", "image/jpeg", ".bin")
        self.assertEqual(ext, ".jpg")

    def test_mp4_content_type(self):
        ext = extension_from_response("http://example.com/file", "video/mp4", ".bin")
        self.assertEqual(ext, ".mp4")

    def test_octet_stream_falls_back_to_suffix(self):
        ext = extension_from_response("http://example.com/photo.png", "application/octet-stream", ".bin")
        self.assertEqual(ext, ".png")

    def test_octet_stream_no_suffix_uses_fallback(self):
        ext = extension_from_response("http://example.com/file", "application/octet-stream", ".bin")
        self.assertEqual(ext, ".bin")

    def test_content_type_with_charset(self):
        ext = extension_from_response("http://example.com/file", "image/webp; charset=utf-8", ".bin")
        self.assertEqual(ext, ".webp")

    def test_url_suffix_used_when_no_content_type_match(self):
        ext = extension_from_response("http://example.com/image.webp", "text/html", ".bin")
        self.assertEqual(ext, ".webp")


class StableFilenameTest(unittest.TestCase):
    def test_deterministic(self):
        a = stable_filename("image", "http://example.com/test.png", ".png")
        b = stable_filename("image", "http://example.com/test.png", ".png")
        self.assertEqual(a, b)

    def test_different_urls_produce_different_names(self):
        a = stable_filename("image", "http://example.com/a.png", ".png")
        b = stable_filename("image", "http://example.com/b.png", ".png")
        self.assertNotEqual(a, b)

    def test_prefix_sanitized(self):
        name = stable_filename("image/provider", "http://example.com/test.png", ".png")
        self.assertTrue(name.startswith("image-provider_"))

    def test_stable_id_overrides_url(self):
        a = stable_filename("image", "http://example.com/a.png", ".png", stable_id="fixed-id")
        b = stable_filename("image", "http://example.com/b.png", ".png", stable_id="fixed-id")
        self.assertEqual(a, b)


class _AtomicWriteTestBase(unittest.TestCase):
    """Shared setUp/tearDown for atomic write tests."""

    def setUp(self):
        self._tmp_dir = tempfile.mkdtemp(prefix="atomic-write-test-")
        self._orig_output_dir = C.OUTPUT_DIR
        self._orig_auto_download = C.AUTO_DOWNLOAD_GENERATED
        C.OUTPUT_DIR = Path(self._tmp_dir) / "output"
        C.OUTPUT_DIR.mkdir()
        C.AUTO_DOWNLOAD_GENERATED = True

    def tearDown(self):
        C.OUTPUT_DIR = self._orig_output_dir
        C.AUTO_DOWNLOAD_GENERATED = self._orig_auto_download
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _count_tmp_parts(self) -> int:
        tmp_dir = C.OUTPUT_DIR / ".tmp"
        if not tmp_dir.exists():
            return 0
        return len(list(tmp_dir.glob("*.part")))

    def _stable_filename(self, url: str, stable_id: str) -> str:
        return stable_filename("image_test", url, ".png", stable_id=stable_id)


# ── 1. 正常下载 ──────────────────────────────────────────

class AtomicWriteSuccessTest(_AtomicWriteTestBase):
    def test_final_file_exists(self):
        async def _run():
            content = b"test image content"
            stable_id = "success-id-1"
            expected = self._stable_filename("http://example.com/ok.png", stable_id)
            final_path = C.OUTPUT_DIR / expected

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(content, "image/png", "http://example.com/ok.png"),
            ):
                await download_remote_media(
                    "http://example.com/ok.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertTrue(final_path.exists())
        asyncio.run(_run())

    def test_content_complete(self):
        async def _run():
            content = b"x" * 2048
            stable_id = "success-id-2"
            expected = self._stable_filename("http://example.com/full.png", stable_id)
            final_path = C.OUTPUT_DIR / expected

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(content, "image/png", "http://example.com/full.png"),
            ):
                await download_remote_media(
                    "http://example.com/full.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertEqual(final_path.read_bytes(), content)
            self.assertEqual(final_path.stat().st_size, len(content))
        asyncio.run(_run())

    def test_no_tmp_part_residual(self):
        async def _run():
            stable_id = "success-id-3"
            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"data", "image/png", "http://example.com/clean.png"),
            ):
                await download_remote_media(
                    "http://example.com/clean.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertEqual(self._count_tmp_parts(), 0)
        asyncio.run(_run())

    def test_local_url_and_path_no_tmp(self):
        async def _run():
            stable_id = "success-id-4"
            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"data", "image/png", "http://example.com/ret.png"),
            ):
                local_url, local_path = await download_remote_media(
                    "http://example.com/ret.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertNotIn(".tmp", local_url)
            self.assertNotIn(".tmp", local_path)
            self.assertNotIn(".part", local_url)
            self.assertNotIn(".part", local_path)
        asyncio.run(_run())


# ── 2. fetch_public_remote_media 抛异常 ─────────────────

class AtomicWriteFetchFailureTest(_AtomicWriteTestBase):
    def test_final_file_not_created(self):
        async def _run():
            stable_id = "fetch-fail-1"
            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                side_effect=RuntimeError("network error"),
            ):
                with self.assertRaises(RuntimeError):
                    await download_remote_media(
                        "http://example.com/fail1.png",
                        prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                    )
            expected = self._stable_filename("http://example.com/fail1.png", stable_id)
            self.assertFalse((C.OUTPUT_DIR / expected).exists())
        asyncio.run(_run())

    def test_part_cleaned_up(self):
        async def _run():
            stable_id = "fetch-fail-2"
            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                side_effect=RuntimeError("timeout"),
            ):
                with self.assertRaises(RuntimeError):
                    await download_remote_media(
                        "http://example.com/fail2.png",
                        prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                    )
            self.assertEqual(self._count_tmp_parts(), 0)
        asyncio.run(_run())

    def test_try_download_returns_original_url(self):
        async def _run():
            remote_url = "http://example.com/fallback.png"
            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                side_effect=RuntimeError("download failed"),
            ):
                local_url, local_path, error = await try_download_remote_media(
                    remote_url, prefix="image_test", fallback_ext=".png", stable_id="fb-1",
                )
            self.assertEqual(local_url, remote_url)
            self.assertEqual(local_path, "")
            self.assertIsNotNone(error)
            self.assertIn("download failed", error)
        asyncio.run(_run())


# ── 3. os.replace 抛 OSError ──────────────────────────────

class AtomicWriteReplaceFailureTest(_AtomicWriteTestBase):
    def test_final_file_not_created(self):
        async def _run():
            stable_id = "replace-fail-1"

            def failing_replace(src, dst):
                raise OSError("permission denied")

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"data", "image/png", "http://example.com/rf1.png"),
            ), patch("angemedia_gateway.media.os.replace", side_effect=failing_replace):
                with self.assertRaises(OSError):
                    await download_remote_media(
                        "http://example.com/rf1.png",
                        prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                    )
            expected = self._stable_filename("http://example.com/rf1.png", stable_id)
            self.assertFalse((C.OUTPUT_DIR / expected).exists())
        asyncio.run(_run())

    def test_part_cleaned_up(self):
        async def _run():
            stable_id = "replace-fail-2"

            def failing_replace(src, dst):
                raise OSError("disk full")

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"data", "image/png", "http://example.com/rf2.png"),
            ), patch("angemedia_gateway.media.os.replace", side_effect=failing_replace):
                with self.assertRaises(OSError):
                    await download_remote_media(
                        "http://example.com/rf2.png",
                        prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                    )
            self.assertEqual(self._count_tmp_parts(), 0)
        asyncio.run(_run())

    def test_try_download_returns_original_url(self):
        async def _run():
            remote_url = "http://example.com/replace-fb.png"

            def failing_replace(src, dst):
                raise OSError("I/O error")

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"data", "image/png", remote_url),
            ), patch("angemedia_gateway.media.os.replace", side_effect=failing_replace):
                local_url, local_path, error = await try_download_remote_media(
                    remote_url, prefix="image_test", fallback_ext=".png", stable_id="rfb-1",
                )
            self.assertEqual(local_url, remote_url)
            self.assertEqual(local_path, "")
            self.assertIsNotNone(error)
        asyncio.run(_run())


# ── 4. final 文件已存在 ───────────────────────────────────

class AtomicWriteExistingFileTest(_AtomicWriteTestBase):
    def test_no_overwrite(self):
        async def _run():
            stable_id = "existing-1"
            expected = self._stable_filename("http://example.com/exist.png", stable_id)
            final_path = C.OUTPUT_DIR / expected
            original = b"original content"
            final_path.write_bytes(original)

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"new content", "image/png", "http://example.com/exist.png"),
            ):
                await download_remote_media(
                    "http://example.com/exist.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertEqual(final_path.read_bytes(), original)
        asyncio.run(_run())

    def test_no_part_created(self):
        async def _run():
            stable_id = "existing-2"
            expected = self._stable_filename("http://example.com/exist2.png", stable_id)
            final_path = C.OUTPUT_DIR / expected
            final_path.write_bytes(b"keep")

            with patch(
                "angemedia_gateway.media.fetch_public_remote_media",
                new_callable=AsyncMock,
                return_value=(b"new", "image/png", "http://example.com/exist2.png"),
            ):
                await download_remote_media(
                    "http://example.com/exist2.png",
                    prefix="image_test", fallback_ext=".png", stable_id=stable_id,
                )
            self.assertEqual(self._count_tmp_parts(), 0)
        asyncio.run(_run())


# ── 5. .tmp 目录不进入 listing ────────────────────────────

class TmpNotInListingTest(unittest.TestCase):
    def test_known_generated_local_paths_excludes_tmp(self):
        paths = known_generated_local_paths()
        for p in paths:
            if p:
                self.assertNotIn("/.tmp/", p.replace("\\", "/"))

    def test_generation_metadata_by_filename_excludes_tmp(self):
        metadata = generation_metadata_by_filename()
        for key in metadata:
            self.assertNotIn(".tmp", key)
            self.assertNotIn(".part", key)


if __name__ == "__main__":
    unittest.main()
