"""图片生成接入 jobs 表的测试。"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "admin123456")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("AUTO_DOWNLOAD_GENERATED", "false")
os.environ.setdefault("SILICONFLOW_API_KEY", "sf-test-secret-value")

import angemedia_gateway.config as C  # noqa: E402
from angemedia_gateway.schemas import ImageRequest  # noqa: E402
from angemedia_gateway.services.media_service import (  # noqa: E402
    MediaService,
    ImageProvidersFailed,
    NoImageProviderAvailable,
)
from angemedia_gateway.state import (  # noqa: E402
    init_db,
    list_jobs,
    get_job,
)


class FakeImageProvider:
    """模拟成功的图片 provider。"""

    def __init__(self, result: dict) -> None:
        self.result = result

    async def generate(self, req: ImageRequest, target: object) -> dict:
        return copy.deepcopy(self.result)


class FakeFailingProvider:
    """模拟失败的图片 provider。"""

    async def generate(self, req: ImageRequest, target: object) -> dict:
        raise RuntimeError("simulated provider failure")


class _ImageJobTestBase(unittest.TestCase):
    """共享 setUp/tearDown。"""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.mkdtemp(prefix="image-job-test-")
        self._db_path = Path(self._tmp_dir) / "test.db"
        self._output_dir = Path(self._tmp_dir) / "output"
        self._upload_dir = Path(self._tmp_dir) / "upload"
        self._output_dir.mkdir()
        self._upload_dir.mkdir()

        self._orig_db = C.DB_FILE
        self._orig_output = C.OUTPUT_DIR
        self._orig_upload = C.UPLOAD_DIR
        self._orig_base_url = C.PUBLIC_BASE_URL

        C.DB_FILE = self._db_path
        C.OUTPUT_DIR = self._output_dir
        C.UPLOAD_DIR = self._upload_dir
        C.PUBLIC_BASE_URL = "http://testserver"
        init_db()
        self.service = MediaService()

    def tearDown(self) -> None:
        C.DB_FILE = self._orig_db
        C.OUTPUT_DIR = self._orig_output
        C.UPLOAD_DIR = self._orig_upload
        C.PUBLIC_BASE_URL = self._orig_base_url
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _count_jobs(self) -> int:
        conn = self._conn()
        try:
            return conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        finally:
            conn.close()

    def _get_job_by_id(self, job_id: str) -> dict | None:
        job = get_job(job_id)
        return job

    def _make_request(self, **overrides) -> ImageRequest:
        defaults = {"prompt": "a cat", "size": "1024x1024", "response_format": "url"}
        defaults.update(overrides)
        return ImageRequest(**defaults)


SUCCESS_RESULT = {
    "created": 1717500000,
    "data": [{"url": "http://testserver/generated/test.png", "revised_prompt": "a cat"}],
}


# ── 1-7. 成功路径 ──────────────────────────────────────

class ImageJobSuccessTest(_ImageJobTestBase):
    """图片生成成功后 job 行为。"""

    def test_success_creates_job(self) -> None:
        """图片生成成功后创建 job。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        self.assertEqual(self._count_jobs(), 1)
        self.assertIn("job_id", result)

    def test_success_job_kind_is_image(self) -> None:
        """成功 job kind == 'image'。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertIsNotNone(job)
        self.assertEqual(job["kind"], "image")

    def test_success_job_status_is_succeeded(self) -> None:
        """成功后 job status == 'succeeded'。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertEqual(job["status"], "succeeded")

    def test_success_job_records_prompt_model_provider(self) -> None:
        """成功 job 记录 prompt/model/provider。"""
        req = self._make_request(prompt="a dog")
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertEqual(job["prompt"], "a dog")
        self.assertEqual(job["provider"], "siliconflow")
        self.assertEqual(job["model"], "kolors")

    def test_success_job_records_duration_ms(self) -> None:
        """成功 job 记录 duration_ms。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertIsNotNone(job["duration_ms"])
        self.assertGreaterEqual(job["duration_ms"], 0)

    def test_response_preserves_data_structure(self) -> None:
        """response 保留原有 data 结构。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertIn("url", result["data"][0])

    def test_response_includes_job_id(self) -> None:
        """response 顶层包含 job_id。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        self.assertIn("job_id", result)
        self.assertIsInstance(result["job_id"], str)
        self.assertTrue(len(result["job_id"]) > 0)


# ── 8-9. generations 和 assets 仍正常 ─────────────────

class ImageJobLegacyRecordsTest(_ImageJobTestBase):
    """generations 和 assets 写入仍正常。"""

    def test_generations_record_still_written(self) -> None:
        """generations 历史记录仍正常。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            await_compat(self.service.create_image(req))
        conn = self._conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
            self.assertGreaterEqual(count, 1)
        finally:
            conn.close()

    def test_asset_still_written(self) -> None:
        """generated asset 写入仍正常。"""
        # 创建真实输出文件，让 _save_generated_asset 能找到它
        fake_file = self._output_dir / "test_asset.png"
        fake_file.write_bytes(b"\x89PNG\r\n")
        fake_result = {
            "created": 1717500000,
            "data": [{"url": f"{C.PUBLIC_BASE_URL}/generated/test_asset.png", "local_path": str(fake_file), "revised_prompt": "a cat"}],
        }
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(fake_result)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            await_compat(self.service.create_image(req))
        conn = self._conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0]
            self.assertGreaterEqual(count, 1)
        finally:
            conn.close()


# ── 10. provider fallback 只创建一个 job ──────────────

class ImageJobFallbackTest(_ImageJobTestBase):
    """provider fallback 只创建一个 job。"""

    def test_fallback_first_fails_second_succeeds_one_job(self) -> None:
        """第一个 provider 失败、第二个成功时，只创建一个 job，最终 succeeded。"""
        from angemedia_gateway.routing import RouteTarget
        req = self._make_request()
        fail_target = RouteTarget(provider="fail_provider", model="fail-model")
        success_target = RouteTarget(provider="ok_provider", model="ok-model")
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {
                 "fail_provider": FakeFailingProvider(),
                 "ok_provider": FakeImageProvider(SUCCESS_RESULT),
             }):
            mock_chain.return_value = [fail_target, success_target]
            result = await_compat(self.service.create_image(req))
        self.assertEqual(self._count_jobs(), 1)
        job = self._get_job_by_id(result["job_id"])
        self.assertEqual(job["status"], "succeeded")


# ── 11-13. 失败路径 ────────────────────────────────────

class ImageJobFailureTest(_ImageJobTestBase):
    """所有 provider 失败时创建 failed job。"""

    def test_all_providers_fail_creates_failed_job(self) -> None:
        """所有 provider 失败时创建 failed job。"""
        from angemedia_gateway.routing import RouteTarget
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {
                 "fail1": FakeFailingProvider(),
                 "fail2": FakeFailingProvider(),
             }):
            mock_chain.return_value = [
                RouteTarget(provider="fail1", model="m1"),
                RouteTarget(provider="fail2", model="m2"),
            ]
            with self.assertRaises(ImageProvidersFailed):
                await_compat(self.service.create_image(req))
        self.assertEqual(self._count_jobs(), 1)
        conn = self._conn()
        try:
            row = conn.execute("SELECT status, error_code, error_message FROM jobs").fetchone()
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["error_code"], "all_providers_failed")
            self.assertTrue(len(row["error_message"]) > 0)
        finally:
            conn.close()

    def test_failed_job_has_error_code_and_message(self) -> None:
        """failed job 包含 error_code / error_message。"""
        from angemedia_gateway.routing import RouteTarget
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"f": FakeFailingProvider()}):
            mock_chain.return_value = [RouteTarget(provider="f", model="m")]
            with self.assertRaises(ImageProvidersFailed):
                await_compat(self.service.create_image(req))
        conn = self._conn()
        try:
            row = conn.execute("SELECT error_code, error_message FROM jobs").fetchone()
            self.assertEqual(row["error_code"], "all_providers_failed")
            # error_message 不泄露 secret
            self.assertNotIn("Bearer", row["error_message"])
            self.assertNotIn("sk-", row["error_message"])
        finally:
            conn.close()

    def test_failed_job_error_message_no_secret_leak(self) -> None:
        """failed job 的 error_message 不泄露 secret。"""
        from angemedia_gateway.routing import RouteTarget
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"f": FakeFailingProvider()}):
            mock_chain.return_value = [RouteTarget(provider="f", model="m")]
            with self.assertRaises(ImageProvidersFailed):
                await_compat(self.service.create_image(req))
        conn = self._conn()
        try:
            row = conn.execute("SELECT error_message FROM jobs").fetchone()
            msg = row["error_message"]
            self.assertNotIn("am-", msg)
            self.assertNotIn("Bearer", msg)
        finally:
            conn.close()

    def test_error_message_redacts_secrets_from_exception_text(self) -> None:
        """异常消息包含 sk-xxx / am-xxx / Bearer 时，error_message 不含原始 secret。"""
        from angemedia_gateway.routing import RouteTarget

        class SecretLeakingProvider:
            async def generate(self, req, target):
                raise RuntimeError("API key sk-leaked-secret-12345 rejected, Bearer am-leaked-token-67890 denied")

        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"leak": SecretLeakingProvider()}):
            mock_chain.return_value = [RouteTarget(provider="leak", model="m")]
            with self.assertRaises(ImageProvidersFailed):
                await_compat(self.service.create_image(req))
        conn = self._conn()
        try:
            row = conn.execute("SELECT error_message FROM jobs").fetchone()
            msg = row["error_message"]
            self.assertNotIn("sk-leaked-secret-12345", msg)
            self.assertNotIn("am-leaked-token-67890", msg)
            self.assertIn("REDACTED", msg)
        finally:
            conn.close()


# ── 补充: built-in 成功 job started_at 非空 ────────────

class ImageJobStartedAtTest(_ImageJobTestBase):
    """built-in 成功 job 的 started_at 非空。"""

    def test_builtin_success_job_started_at_non_null(self) -> None:
        """built-in 成功 job 的 started_at 非空。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertIsNotNone(job["started_at"])
        self.assertIn("T", job["started_at"])


# ── 14-15. job 写入失败不阻断 ─────────────────────────

class ImageJobGracefulDegradationTest(_ImageJobTestBase):
    """job 写入失败时，图片生成仍正常。"""

    def test_create_job_failure_does_not_block_request(self) -> None:
        """mock create_job 抛异常时，图片生成成功 response 仍为 200，且不包含 job_id。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}), \
             patch("angemedia_gateway.services.media_service.create_job", side_effect=RuntimeError("simulated DB failure")):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)
        self.assertNotIn("job_id", result)

    def test_update_job_failure_does_not_block_request(self) -> None:
        """mock update_job_status 抛异常时，图片生成成功 response 仍为 200。"""
        req = self._make_request()
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(SUCCESS_RESULT)}), \
             patch("angemedia_gateway.services.media_service.update_job_status", side_effect=RuntimeError("simulated DB failure")):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        self.assertIn("data", result)
        self.assertEqual(len(result["data"]), 1)


# ── 16. b64_json 不存完整 base64 ───────────────────────

class ImageJobOutputJsonTest(_ImageJobTestBase):
    """output_json 不存储完整 b64 内容。"""

    def test_b64_response_not_stored_in_output_json(self) -> None:
        """b64_json response 不得把完整 base64 写入 jobs.output_json。"""
        b64_result = {
            "created": 1717500000,
            "data": [{"b64_json": "A" * 10000, "revised_prompt": "a cat"}],
        }
        req = self._make_request(response_format="b64_json")
        with patch("angemedia_gateway.services.media_service.resolve_chain") as mock_chain, \
             patch("angemedia_gateway.services.media_service.PROVIDERS", {"siliconflow": FakeImageProvider(b64_result)}), \
             patch("angemedia_gateway.services.media_service.maybe_to_b64", return_value=b64_result):
            mock_chain.return_value = [type("T", (), {"provider": "siliconflow", "model": "kolors"})()]
            result = await_compat(self.service.create_image(req))
        job = self._get_job_by_id(result["job_id"])
        self.assertIsNotNone(job)
        output = json.loads(job["output_json"])
        self.assertTrue(output["has_b64_json"])
        self.assertFalse(output["has_url"])
        # 完整 b64 不在 output_json 中
        self.assertNotIn("A" * 10000, job["output_json"])


def await_compat(coro):
    """兼容同步测试调用异步方法。"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
