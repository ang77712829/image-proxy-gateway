"""assets CRUD 函数测试。"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.state import init_db, save_asset, get_asset, list_assets, delete_asset


class _AssetCrudTestBase(TestCase):
    """共享 setUp/tearDown：独立临时 DB + assets 表 + 隔离存储目录。"""

    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self._tmp.name
        self._tmp.close()
        self._tmp_dir = tempfile.mkdtemp(prefix="crud_test_")
        self.output_dir = Path(self._tmp_dir) / "output"
        self.upload_dir = Path(self._tmp_dir) / "upload"
        self.output_dir.mkdir()
        self.upload_dir.mkdir()
        import angemedia_gateway.config as C
        self._orig_db = C.DB_FILE
        self._orig_output = C.OUTPUT_DIR
        self._orig_upload = C.UPLOAD_DIR
        self._config_mod = C
        C.DB_FILE = Path(self.db_path)
        C.OUTPUT_DIR = self.output_dir
        C.UPLOAD_DIR = self.upload_dir
        init_db()

    def tearDown(self) -> None:
        self._config_mod.DB_FILE = self._orig_db
        self._config_mod.OUTPUT_DIR = self._orig_output
        self._config_mod.UPLOAD_DIR = self._orig_upload
        os.unlink(self.db_path)
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _read_asset(self, asset_id: str) -> dict | None:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()


class SaveAssetTest(_AssetCrudTestBase):
    """save_asset 基本插入。"""

    def test_insert_new_asset(self) -> None:
        """插入新资产成功。"""
        save_asset(
            id="a-001",
            filename="img.png",
            storage_area="output",
            relative_path="img.png",
            url_path="/generated/img.png",
            media_type="image",
            source="generated",
            size=1024,
        )
        asset = self._read_asset("a-001")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["filename"], "img.png")
        self.assertEqual(asset["storage_area"], "output")

    def test_insert_with_optional_fields(self) -> None:
        """可选字段写入正确。"""
        save_asset(
            id="a-002",
            filename="vid.mp4",
            storage_area="output",
            relative_path="vid.mp4",
            url_path="/generated/vid.mp4",
            media_type="video",
            source="generated",
            size=4096,
            prompt="a cat",
            model="model-x",
            provider="test-provider",
            duration_ms=5000,
        )
        asset = self._read_asset("a-002")
        self.assertEqual(asset["prompt"], "a cat")
        self.assertEqual(asset["model"], "model-x")
        self.assertEqual(asset["provider"], "test-provider")
        self.assertEqual(asset["duration_ms"], 5000)

    def test_optional_fields_default_null(self) -> None:
        """未传可选字段为 NULL。"""
        save_asset(
            id="a-003",
            filename="img2.png",
            storage_area="output",
            relative_path="img2.png",
            url_path="/generated/img2.png",
            media_type="image",
            source="generated",
            size=512,
        )
        asset = self._read_asset("a-003")
        self.assertIsNone(asset["prompt"])
        self.assertIsNone(asset["model"])
        self.assertIsNone(asset["provider"])
        self.assertIsNone(asset["duration_ms"])

    def test_created_at_is_set(self) -> None:
        """created_at 在首次插入时被设置，格式为 ISO 8601。"""
        save_asset(
            id="a-004",
            filename="img3.png",
            storage_area="output",
            relative_path="img3.png",
            url_path="/generated/img3.png",
            media_type="image",
            source="generated",
            size=256,
        )
        asset = self._read_asset("a-004")
        created = asset["created_at"]
        self.assertIsInstance(created, str)
        self.assertGreater(len(created), 0)
        # ISO 8601 datetime 至少包含 'T' 分隔日期和时间
        self.assertIn("T", created)
        # 可被 datetime.fromisoformat 解析
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(created)
        self.assertEqual(dt.tzinfo, timezone.utc)


class SaveAssetConflictTest(_AssetCrudTestBase):
    """save_asset ON CONFLICT 行为。"""

    def test_same_key_updates_metadata(self) -> None:
        """相同 (storage_area, relative_path) 触发 UPDATE，保留原 id。"""
        save_asset(
            id="a-010",
            filename="old.png",
            storage_area="output",
            relative_path="conflict.png",
            url_path="/generated/conflict.png",
            media_type="image",
            source="generated",
            size=100,
        )
        save_asset(
            id="a-011",
            filename="new.png",
            storage_area="output",
            relative_path="conflict.png",
            url_path="/generated/conflict.png",
            media_type="image",
            source="generated",
            size=200,
        )
        # 原 id 保留，新 id 不产生记录
        asset = self._read_asset("a-010")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["filename"], "new.png")
        self.assertEqual(asset["size"], 200)
        self.assertIsNone(self._read_asset("a-011"))

    def test_conflict_preserves_original_id(self) -> None:
        """冲突时保留原 id，即使传入不同 id。"""
        save_asset(
            id="original-id",
            filename="v1.png",
            storage_area="output",
            relative_path="id-test.png",
            url_path="/generated/id-test.png",
            media_type="image",
            source="generated",
            size=100,
        )
        save_asset(
            id="different-id",
            filename="v2.png",
            storage_area="output",
            relative_path="id-test.png",
            url_path="/generated/id-test.png",
            media_type="image",
            source="generated",
            size=200,
        )
        # 原 id 仍存在
        asset = self._read_asset("original-id")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["filename"], "v2.png")
        # 新 id 不存在
        self.assertIsNone(self._read_asset("different-id"))

    def test_conflict_preserves_created_at(self) -> None:
        """冲突更新不覆盖 created_at。"""
        save_asset(
            id="a-020",
            filename="v1.png",
            storage_area="output",
            relative_path="keep-time.png",
            url_path="/generated/keep-time.png",
            media_type="image",
            source="generated",
            size=100,
        )
        original = self._read_asset("a-020")
        original_created = original["created_at"]

        import time
        time.sleep(0.05)

        save_asset(
            id="a-021",
            filename="v2.png",
            storage_area="output",
            relative_path="keep-time.png",
            url_path="/generated/keep-time.png",
            media_type="image",
            source="generated",
            size=300,
            prompt="updated prompt",
        )
        # 原 id 保留，通过原 id 查询
        updated = self._read_asset("a-020")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["created_at"], original_created)
        self.assertEqual(updated["prompt"], "updated prompt")

    def test_no_duplicate_rows_on_conflict(self) -> None:
        """冲突后不产生重复行。"""
        save_asset(
            id="a-030",
            filename="dup1.png",
            storage_area="output",
            relative_path="no-dup.png",
            url_path="/generated/no-dup.png",
            media_type="image",
            source="generated",
            size=100,
        )
        save_asset(
            id="a-031",
            filename="dup2.png",
            storage_area="output",
            relative_path="no-dup.png",
            url_path="/generated/no-dup.png",
            media_type="image",
            source="generated",
            size=200,
        )
        conn = sqlite3.connect(self.db_path)
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM assets WHERE storage_area = 'output' AND relative_path = 'no-dup.png'"
            ).fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()


class SaveAssetIntegrityErrorTest(_AssetCrudTestBase):
    """save_asset IntegrityError 处理。"""

    def test_invalid_storage_area_raises_400(self) -> None:
        """非法 storage_area 触发 IntegrityError → HTTPException 400。"""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            save_asset(
                id="a-040",
                filename="bad.png",
                storage_area="invalid_area",
                relative_path="bad.png",
                url_path="/bad.png",
                media_type="image",
                source="generated",
                size=100,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_invalid_media_type_raises_400(self) -> None:
        """非法 media_type 触发 IntegrityError → HTTPException 400。"""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            save_asset(
                id="a-041",
                filename="bad2.png",
                storage_area="output",
                relative_path="bad2.png",
                url_path="/bad2.png",
                media_type="audio",
                source="generated",
                size=100,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_invalid_source_raises_400(self) -> None:
        """非法 source 触发 IntegrityError → HTTPException 400。"""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            save_asset(
                id="a-042",
                filename="bad3.png",
                storage_area="output",
                relative_path="bad3.png",
                url_path="/bad3.png",
                media_type="image",
                source="downloaded",
                size=100,
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_integrity_error_does_not_leak(self) -> None:
        """IntegrityError 被转为 HTTPException，调用方不会收到原始 IntegrityError。"""
        from fastapi import HTTPException
        try:
            save_asset(
                id="a-043",
                filename="bad4.png",
                storage_area="nope",
                relative_path="bad4.png",
                url_path="/bad4.png",
                media_type="image",
                source="generated",
                size=100,
            )
            self.fail("应抛出 HTTPException")
        except HTTPException as exc:
            # __cause__ 可以是 IntegrityError（用于调试链），但不能是调用方直接收到的类型
            self.assertEqual(exc.status_code, 400)
        except sqlite3.IntegrityError:
            self.fail("不应泄漏原始 IntegrityError 给调用方")


class GetAssetTest(_AssetCrudTestBase):
    """get_asset 查询。"""

    def test_returns_asset(self) -> None:
        """存在时返回 dict。"""
        save_asset(
            id="a-050",
            filename="find.png",
            storage_area="output",
            relative_path="find.png",
            url_path="/generated/find.png",
            media_type="image",
            source="generated",
            size=100,
        )
        asset = get_asset("a-050")
        self.assertIsNotNone(asset)
        self.assertEqual(asset["id"], "a-050")

    def test_returns_none_missing(self) -> None:
        """不存在时返回 None。"""
        self.assertIsNone(get_asset("nonexistent-id"))


class ListAssetsTest(_AssetCrudTestBase):
    """list_assets 分页与排序。"""

    def _insert_n(self, n: int, base_storage: str = "output") -> None:
        """插入 n 条资产。"""
        for i in range(n):
            save_asset(
                id=f"list-{i:03d}",
                filename=f"item{i}.png",
                storage_area=base_storage,
                relative_path=f"item{i}.png",
                url_path=f"/generated/item{i}.png",
                media_type="image",
                source="generated",
                size=100 + i,
            )

    def test_returns_descending_by_created_at(self) -> None:
        """结果按 created_at DESC 排序。"""
        self._insert_n(5)
        assets = list_assets(limit=10)
        self.assertEqual(len(assets), 5)
        timestamps = [a["created_at"] for a in assets]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_limit_controls_count(self) -> None:
        """limit 控制返回数量。"""
        self._insert_n(10)
        assets = list_assets(limit=3)
        self.assertEqual(len(assets), 3)

    def test_offset_skips_records(self) -> None:
        """offset 跳过前 N 条。"""
        self._insert_n(5)
        all_assets = list_assets(limit=10)
        page2 = list_assets(limit=3, offset=3)
        self.assertEqual(len(page2), 2)
        self.assertEqual(page2[0]["id"], all_assets[3]["id"])

    def test_empty_table_returns_empty(self) -> None:
        """空表返回空列表。"""
        self.assertEqual(list_assets(), [])


class DeleteAssetTest(_AssetCrudTestBase):
    """delete_asset 删除记录与文件。"""

    def test_returns_false_when_missing(self) -> None:
        """不存在的资产返回 False。"""
        self.assertFalse(delete_asset("nonexistent"))

    def test_deletes_db_record(self) -> None:
        """删除后记录不存在。"""
        save_asset(
            id="del-001",
            filename="to-delete.png",
            storage_area="output",
            relative_path="to-delete.png",
            url_path="/generated/to-delete.png",
            media_type="image",
            source="generated",
            size=100,
        )
        result = delete_asset("del-001")
        self.assertTrue(result)
        self.assertIsNone(self._read_asset("del-001"))

    def test_returns_true_when_record_exists(self) -> None:
        """存在时返回 True。"""
        save_asset(
            id="del-002",
            filename="exists.png",
            storage_area="upload",
            relative_path="exists.png",
            url_path="/uploads/exists.png",
            media_type="image",
            source="upload",
            size=100,
        )
        self.assertTrue(delete_asset("del-002"))

    def test_handles_file_already_deleted(self) -> None:
        """文件已不存在时仍能成功删除记录。"""
        save_asset(
            id="del-003",
            filename="no-file.png",
            storage_area="output",
            relative_path="no-file.png",
            url_path="/generated/no-file.png",
            media_type="image",
            source="generated",
            size=100,
        )
        # No actual file created, delete_asset should handle gracefully
        result = delete_asset("del-003")
        self.assertTrue(result)
        self.assertIsNone(self._read_asset("del-003"))

    def test_deletes_actual_file(self) -> None:
        """output 存储区：存在物理文件时一并删除。"""
        real_file = self.output_dir / "real-delete.png"
        real_file.write_bytes(b"fake image data")
        self.assertTrue(real_file.exists())

        save_asset(
            id="del-004",
            filename="real-delete.png",
            storage_area="output",
            relative_path="real-delete.png",
            url_path="/generated/real-delete.png",
            media_type="image",
            source="generated",
            size=15,
        )
        result = delete_asset("del-004")
        self.assertTrue(result)
        self.assertFalse(real_file.exists(), "物理文件应被删除")
        self.assertIsNone(self._read_asset("del-004"))

    def test_deletes_upload_file(self) -> None:
        """upload 存储区：存在物理文件时从 UPLOAD_DIR 删除。"""
        upload_file = self.upload_dir / "up-delete.png"
        upload_file.write_bytes(b"upload data")
        self.assertTrue(upload_file.exists())

        save_asset(
            id="del-006",
            filename="up-delete.png",
            storage_area="upload",
            relative_path="up-delete.png",
            url_path="/uploads/up-delete.png",
            media_type="image",
            source="upload",
            size=12,
        )
        result = delete_asset("del-006")
        self.assertTrue(result)
        self.assertFalse(upload_file.exists(), "upload 物理文件应被删除")
        self.assertIsNone(self._read_asset("del-006"))
        # 确认 output 目录未被误触
        self.assertTrue(self.output_dir.exists())

    def test_safe_unlink_exception_preserves_db_record(self) -> None:
        """safe_unlink_under 抛异常时 DB 记录不被删除。"""
        from fastapi import HTTPException
        save_asset(
            id="del-005",
            filename="protected.png",
            storage_area="output",
            relative_path="protected.png",
            url_path="/generated/protected.png",
            media_type="image",
            source="generated",
            size=100,
        )
        def _always_reject(path_text: str, base_dir: Path) -> bool:
            raise HTTPException(status_code=400, detail="拒绝删除目录外文件")

        with patch("angemedia_gateway.repositories.assets.safe_unlink_under", side_effect=_always_reject):
            with self.assertRaises(HTTPException):
                delete_asset("del-005")
        # DB 记录应保留
        self.assertIsNotNone(self._read_asset("del-005"))


# ── Phase 2.6-2: assets.job_id CRUD tests ─────────────

class AssetJobIdTest(_AssetCrudTestBase):
    """save_asset / get_asset / list_assets 的 job_id 支持。"""

    def test_save_asset_with_job_id(self) -> None:
        """save_asset(job_id=...) 可保存 job_id。"""
        save_asset(
            id="jid-001", filename="j.png", storage_area="output",
            relative_path="jid.png", url_path="/generated/jid.png",
            media_type="image", source="generated", size=100,
            job_id="job-abc",
        )
        asset = self._read_asset("jid-001")
        self.assertEqual(asset["job_id"], "job-abc")

    def test_save_asset_without_job_id_is_null(self) -> None:
        """save_asset() 不传 job_id 时 job_id 为 NULL。"""
        save_asset(
            id="jid-002", filename="n.png", storage_area="output",
            relative_path="null-jid.png", url_path="/generated/null-jid.png",
            media_type="image", source="generated", size=100,
        )
        asset = self._read_asset("jid-002")
        self.assertIsNone(asset["job_id"])

    def test_get_asset_returns_dict_with_job_id(self) -> None:
        """get_asset() 返回 dict 包含 job_id。"""
        save_asset(
            id="jid-003", filename="r.png", storage_area="output",
            relative_path="ret-jid.png", url_path="/generated/ret-jid.png",
            media_type="image", source="generated", size=100,
            job_id="job-xyz",
        )
        asset = get_asset("jid-003")
        self.assertIsNotNone(asset)
        self.assertIn("job_id", asset)
        self.assertEqual(asset["job_id"], "job-xyz")

    def test_list_assets_includes_job_id(self) -> None:
        """list_assets() 返回项包含 job_id。"""
        save_asset(
            id="jid-004", filename="l.png", storage_area="output",
            relative_path="list-jid.png", url_path="/generated/list-jid.png",
            media_type="image", source="generated", size=100,
            job_id="job-list",
        )
        assets = list_assets()
        self.assertEqual(len(assets), 1)
        self.assertIn("job_id", assets[0])
        self.assertEqual(assets[0]["job_id"], "job-list")

    def test_list_assets_filter_by_job_id(self) -> None:
        """list_assets(job_id=...) 只返回匹配 job_id 的 assets。"""
        save_asset(
            id="jid-005a", filename="a.png", storage_area="output",
            relative_path="filter-a.png", url_path="/generated/filter-a.png",
            media_type="image", source="generated", size=100,
            job_id="job-match",
        )
        save_asset(
            id="jid-005b", filename="b.png", storage_area="output",
            relative_path="filter-b.png", url_path="/generated/filter-b.png",
            media_type="image", source="generated", size=100,
            job_id="job-other",
        )
        assets = list_assets(job_id="job-match")
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["job_id"], "job-match")

    def test_list_assets_filter_no_match(self) -> None:
        """list_assets(job_id=...) 无匹配时返回空列表。"""
        save_asset(
            id="jid-006", filename="c.png", storage_area="output",
            relative_path="no-match.png", url_path="/generated/no-match.png",
            media_type="image", source="generated", size=100,
            job_id="job-x",
        )
        assets = list_assets(job_id="job-nonexistent")
        self.assertEqual(assets, [])

    def test_old_call_without_job_id_still_works(self) -> None:
        """旧调用不传 job_id 仍成功。"""
        save_asset(
            id="jid-007", filename="old.png", storage_area="output",
            relative_path="old-style.png", url_path="/generated/old-style.png",
            media_type="image", source="generated", size=100,
        )
        asset = self._read_asset("jid-007")
        self.assertIsNotNone(asset)
        self.assertIsNone(asset["job_id"])

    def test_same_path_same_job_id_idempotent(self) -> None:
        """同一路径重复 save_asset(job_id=同一个值) 幂等。"""
        save_asset(
            id="jid-008a", filename="idem.png", storage_area="output",
            relative_path="idem.png", url_path="/generated/idem.png",
            media_type="image", source="generated", size=100,
            job_id="job-idem",
        )
        save_asset(
            id="jid-008b", filename="idem2.png", storage_area="output",
            relative_path="idem.png", url_path="/generated/idem.png",
            media_type="image", source="generated", size=200,
            job_id="job-idem",
        )
        asset = self._read_asset("jid-008a")
        self.assertEqual(asset["job_id"], "job-idem")
        self.assertEqual(asset["size"], 200)
        self.assertIsNone(self._read_asset("jid-008b"))

    def test_null_job_id_does_not_overwrite_existing(self) -> None:
        """已有 asset job_id=old 时，save_asset(job_id=None) 不覆盖。"""
        save_asset(
            id="jid-009a", filename="keep.png", storage_area="output",
            relative_path="keep-job.png", url_path="/generated/keep-job.png",
            media_type="image", source="generated", size=100,
            job_id="job-keep",
        )
        # 再次保存但不传 job_id
        save_asset(
            id="jid-009b", filename="keep2.png", storage_area="output",
            relative_path="keep-job.png", url_path="/generated/keep-job.png",
            media_type="image", source="generated", size=200,
        )
        asset = self._read_asset("jid-009a")
        self.assertEqual(asset["job_id"], "job-keep")
        self.assertEqual(asset["size"], 200)

    def test_non_null_job_id_can_fill_null(self) -> None:
        """已有 asset job_id=NULL 时，save_asset(job_id=新值) 可以补写。"""
        save_asset(
            id="jid-010a", filename="fill.png", storage_area="output",
            relative_path="fill-job.png", url_path="/generated/fill-job.png",
            media_type="image", source="generated", size=100,
        )
        # 补写 job_id
        save_asset(
            id="jid-010b", filename="fill2.png", storage_area="output",
            relative_path="fill-job.png", url_path="/generated/fill-job.png",
            media_type="image", source="generated", size=200,
            job_id="job-filled",
        )
        asset = self._read_asset("jid-010a")
        self.assertEqual(asset["job_id"], "job-filled")
        self.assertEqual(asset["size"], 200)

    def test_different_job_id_does_not_overwrite_existing(self) -> None:
        """已有 asset job_id=old 时，save_asset(job_id=new) 不覆盖 old。"""
        save_asset(
            id="jid-011a", filename="over.png", storage_area="output",
            relative_path="over-job.png", url_path="/generated/over-job.png",
            media_type="image", source="generated", size=100,
            job_id="job-old",
        )
        save_asset(
            id="jid-011b", filename="over2.png", storage_area="output",
            relative_path="over-job.png", url_path="/generated/over-job.png",
            media_type="image", source="generated", size=200,
            job_id="job-new",
        )
        asset = self._read_asset("jid-011a")
        # job_id 不被覆盖，仍为 job-old
        self.assertEqual(asset["job_id"], "job-old")
        # metadata 如 size 仍按原有冲突逻辑更新
        self.assertEqual(asset["size"], 200)
        self.assertEqual(asset["filename"], "over2.png")
        # 不新增重复行
        self.assertIsNone(self._read_asset("jid-011b"))

    def test_delete_asset_with_job_id_succeeds(self) -> None:
        """delete_asset() 删除含 job_id 的 asset 不报错。"""
        save_asset(
            id="jid-012", filename="del-jid.png", storage_area="output",
            relative_path="del-jid.png", url_path="/generated/del-jid.png",
            media_type="image", source="generated", size=100,
            job_id="job-del",
        )
        self.assertTrue(delete_asset("jid-012"))
        self.assertIsNone(self._read_asset("jid-012"))
