"""视频提交路径接入 jobs 表的测试。"""
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
from unittest.mock import patch, AsyncMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_DEFAULT_PASSWORD", "admin123456")
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")
os.environ.setdefault("AUTO_DOWNLOAD_GENERATED", "false")
os.environ.setdefault("SILICONFLOW_API_KEY", "sf-test-secret-value")

import angemedia_gateway.config as C  # noqa: E402
from angemedia_gateway.schemas import VideoRequest  # noqa: E402
from angemedia_gateway.services.media_service import (  # noqa: E402
    MediaService,
    VideoProviderDisabled,
)
from angemedia_gateway.state import (  # noqa: E402
    init_db,
    get_job,
)


class _VideoJobTestBase(unittest.TestCase):
    """共享 setUp/tearDown。"""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.mkdtemp(prefix="video-job-test-")
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

    def _make_request(self, **overrides) -> VideoRequest:
        defaults = {"prompt": "a cat walking", "model": "agnes-video-v2.0"}
        defaults.update(overrides)
        return VideoRequest(**defaults)

    def _mock_agnes_submit(self, task_id: str = "agnes-task-001", status: str = "queued"):
        """返回 mock submit_task 方法。"""
        mock = AsyncMock(return_value={
            "task_id": task_id,
            "status": status,
            "provider": "agnes_video",
        })
        return mock


# ── 1-7. 异步提交成功路径 ──────────────────────────────

class VideoJobSubmitSuccessTest(_VideoJobTestBase):
    """视频异步提交成功后 job 行为。"""

    def test_submit_creates_video_job(self) -> None:
        """异步提交成功后创建 video job。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            mock_av.normalize_submit = lambda data: data
            from angemedia_gateway.services.media_service import builtin_provider_enabled
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        self.assertEqual(self._count_jobs(), 1)
        self.assertIn("job_id", result)

    def test_job_kind_is_video(self) -> None:
        """job kind == 'video'。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        self.assertIsNotNone(job)
        self.assertEqual(job["kind"], "video")

    def test_job_status_is_running(self) -> None:
        """异步提交 job status == 'running'。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit(status="queued")
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        self.assertEqual(job["status"], "running")

    def test_job_records_prompt_model_provider(self) -> None:
        """job 记录 prompt/model/provider。"""
        req = self._make_request(prompt="a dog running")
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        self.assertEqual(job["prompt"], "a dog running")
        self.assertEqual(job["provider"], "agnes_video")
        self.assertEqual(job["model"], "agnes-video-v2.0")

    def test_job_records_external_task_id(self) -> None:
        """job external_task_id 等于 Agnes task_id。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit(task_id="agnes-xyz-789")
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        self.assertEqual(job["external_task_id"], "agnes-xyz-789")
        self.assertEqual(result["task_id"], "agnes-xyz-789")

    def test_response_preserves_task_id_and_status(self) -> None:
        """response 保留原有 task_id/status 字段。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit(task_id="tid-001", status="queued")
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        self.assertEqual(result["task_id"], "tid-001")
        self.assertIn("status", result)

    def test_response_includes_job_id(self) -> None:
        """response 顶层包含 job_id。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        self.assertIn("job_id", result)
        self.assertIsInstance(result["job_id"], str)
        self.assertTrue(len(result["job_id"]) > 0)


# ── 8-10. 现有表行为仍正常 ────────────────────────────

class VideoJobLegacyRecordsTest(_VideoJobTestBase):
    """video_tasks / generations / assets 写入仍正常。"""

    def test_video_tasks_still_written(self) -> None:
        """video_tasks 表仍正常写入。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit(task_id="vt-001")
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                await_compat(self.service.create_video(req))
        conn = self._conn()
        try:
            row = conn.execute("SELECT task_id FROM video_tasks WHERE task_id = 'vt-001'").fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()

    def test_generations_still_written(self) -> None:
        """generations 表仍正常写入。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                await_compat(self.service.create_video(req))
        conn = self._conn()
        try:
            count = conn.execute("SELECT COUNT(*) FROM generations WHERE media_type = 'video'").fetchone()[0]
            self.assertGreaterEqual(count, 1)
        finally:
            conn.close()


# ── 11. job 创建失败不阻断 ────────────────────────────

class VideoJobGracefulDegradationTest(_VideoJobTestBase):
    """job 创建失败时，视频提交仍正常。"""

    def test_create_job_failure_does_not_block_request(self) -> None:
        """mock create_job 抛异常时，视频提交仍返回成功，且不包含 job_id。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True), \
                 patch("angemedia_gateway.services.media_service.create_job", side_effect=RuntimeError("DB failure")):
                result = await_compat(self.service.create_video(req))
        self.assertIn("task_id", result)
        self.assertNotIn("job_id", result)


# ── 12. submit_task 失败不创建 job ────────────────────

class VideoJobSubmitFailureTest(_VideoJobTestBase):
    """submit_task 失败时不创建 job。"""

    def test_submit_failure_no_job_created(self) -> None:
        """submit_task 失败时不创建 job，原异常行为不变。"""
        req = self._make_request()
        mock_submit = AsyncMock(side_effect=RuntimeError("Agnes API error"))
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                with self.assertRaises(RuntimeError):
                    await_compat(self.service.create_video(req))
        self.assertEqual(self._count_jobs(), 0)


# ── 13. input_json 安全 ───────────────────────────────

class VideoJobInputJsonTest(_VideoJobTestBase):
    """input_json 安全设计。"""

    def test_input_json_excludes_image_urls(self) -> None:
        """input_json 不保存原始 image/images URL。"""
        req = self._make_request(image="https://example.com/secret-token.png", images=["https://a.com/1.png", "https://b.com/2.png"])
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        input_data = json.loads(job["input_json"])
        # 不包含原始 URL
        self.assertNotIn("image", input_data)
        self.assertNotIn("images", input_data)
        # 包含摘要
        self.assertTrue(input_data["has_image"])
        self.assertEqual(input_data["image_count"], 2)

    def test_input_json_has_safe_fields(self) -> None:
        """input_json 包含安全字段。"""
        req = self._make_request(mode="keyframes", height=512, width=768, num_frames=81, frame_rate=30)
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        job = get_job(result["job_id"])
        input_data = json.loads(job["input_json"])
        self.assertEqual(input_data["model"], "agnes-video-v2.0")
        self.assertEqual(input_data["mode"], "keyframes")
        self.assertEqual(input_data["height"], 512)
        self.assertEqual(input_data["width"], 768)
        self.assertEqual(input_data["num_frames"], 81)
        self.assertEqual(input_data["frame_rate"], 30)
        self.assertFalse(input_data["wait_for_completion"])


# ── 14. response 不泄露 secret ────────────────────────

class VideoJobSecretLeakTest(_VideoJobTestBase):
    """response 不泄露 secret。"""

    def test_response_no_secret_leak(self) -> None:
        """response 不包含真实 Agnes API key / Bearer / env secret。"""
        req = self._make_request()
        mock_submit = self._mock_agnes_submit()
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.submit_task = mock_submit
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        # 验证 response 中不包含环境变量中的 secret
        result_str = json.dumps(result)
        self.assertNotIn(C.SILICONFLOW_API_KEY, result_str)
        self.assertNotIn("AGNES_API_KEY", result_str)
        # 验证 input_json 也不泄露
        if "job_id" in result:
            job = get_job(result["job_id"])
            self.assertNotIn(C.SILICONFLOW_API_KEY, job["input_json"])


# ── 15. GET /v1/videos/{task_id} 未修改 ───────────────

class VideoJobGetVideoUnchangedTest(_VideoJobTestBase):
    """GET /v1/videos/{task_id} 行为不变。"""

    def test_get_video_not_modified(self) -> None:
        """get_video 方法未被修改，仍正常工作。"""
        mock_poll = AsyncMock(return_value={
            "task_id": "existing-task",
            "status": "completed",
            "video_url": "http://example.com/video.mp4",
        })
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.poll_task = mock_poll
            result = await_compat(self.service.get_video("existing-task"))
        self.assertEqual(result["task_id"], "existing-task")
        self.assertEqual(result["status"], "completed")


# ── 16-17. wait_for_completion=true 不创建 job ────────

class VideoJobSyncPathTest(_VideoJobTestBase):
    """wait_for_completion=true 路径不创建 job。"""

    def test_sync_path_no_job_created(self) -> None:
        """wait_for_completion=true 时不创建 job。"""
        req = self._make_request(wait_for_completion=True)
        mock_generate = AsyncMock(return_value={
            "task_id": "sync-task-001",
            "status": "completed",
            "video_url": "http://example.com/video.mp4",
        })
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.generate_video = mock_generate
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                await_compat(self.service.create_video(req))
        self.assertEqual(self._count_jobs(), 0)

    def test_sync_path_response_no_job_id(self) -> None:
        """wait_for_completion=true response 不包含 job_id。"""
        req = self._make_request(wait_for_completion=True)
        mock_generate = AsyncMock(return_value={
            "task_id": "sync-task-002",
            "status": "completed",
            "video_url": "http://example.com/video.mp4",
        })
        with patch("angemedia_gateway.services.media_service.agnes_video") as mock_av:
            mock_av.generate_video = mock_generate
            with patch("angemedia_gateway.services.media_service.builtin_provider_enabled", return_value=True):
                result = await_compat(self.service.create_video(req))
        self.assertNotIn("job_id", result)
        self.assertIn("task_id", result)


def await_compat(coro):
    """兼容同步测试调用异步方法。"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
