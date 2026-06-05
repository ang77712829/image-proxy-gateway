"""assets 表 schema 验证测试。"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.state import init_db


def _get_assets_columns(db_path: str) -> list[dict]:
    """返回 assets 表的列信息。"""
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("PRAGMA table_info(assets)").fetchall()
        return [{"name": row[1], "type": row[2], "notnull": row[3], "default": row[4], "pk": row[5]} for row in rows]
    finally:
        conn.close()


def _table_exists(db_path: str, table_name: str) -> bool:
    """检查表是否存在。"""
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def _insert_asset(db_path: str, **overrides) -> None:
    """向 assets 表插入一条记录，用于 CHECK 约束测试。"""
    defaults = {
        "id": "test-001",
        "filename": "test.png",
        "storage_area": "output",
        "relative_path": "test.png",
        "url_path": "/generated/test.png",
        "media_type": "image",
        "source": "generated",
        "size": 1024,
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    defaults.update(overrides)
    cols = ", ".join(defaults.keys())
    placeholders = ", ".join(["?"] * len(defaults))
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(f"INSERT INTO assets({cols}) VALUES({placeholders})", list(defaults.values()))
        conn.commit()
    finally:
        conn.close()


class AssetsSchemaTest(TestCase):
    """验证 init_db 创建的 assets 表结构。"""

    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self._tmp.name
        self._tmp.close()
        import angemedia_gateway.config as C
        self._orig_db = C.DB_FILE
        try:
            C.DB_FILE = Path(self.db_path)
            init_db()
        finally:
            C.DB_FILE = self._orig_db

    def tearDown(self) -> None:
        import os
        os.unlink(self.db_path)

    def test_assets_table_exists(self) -> None:
        """assets 表被创建。"""
        self.assertTrue(_table_exists(self.db_path, "assets"))

    def test_assets_has_13_columns(self) -> None:
        """assets 表恰好 13 个字段。"""
        cols = _get_assets_columns(self.db_path)
        self.assertEqual(len(cols), 13)

    def test_assets_expected_columns(self) -> None:
        """assets 表包含所有预期字段。"""
        cols = {c["name"] for c in _get_assets_columns(self.db_path)}
        expected = {
            "id", "filename", "storage_area", "relative_path", "url_path",
            "media_type", "source", "size", "prompt", "model", "provider",
            "duration_ms", "created_at",
        }
        self.assertEqual(cols, expected)

    def test_id_is_primary_key(self) -> None:
        """id 字段是主键。"""
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        self.assertEqual(cols["id"]["pk"], 1)

    def test_duration_ms_allows_null(self) -> None:
        """duration_ms 允许 NULL。"""
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        self.assertEqual(cols["duration_ms"]["notnull"], 0)

    def test_size_default_is_zero(self) -> None:
        """size 字段默认值为 0。"""
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        self.assertIn(cols["size"]["default"], ("0", 0))

    def test_required_fields_not_null(self) -> None:
        """必填字段不允许 NULL（id 是主键，隐式 NOT NULL，不检查 notnull 列）。"""
        required = {"filename", "storage_area", "relative_path", "url_path", "media_type", "source", "size", "created_at"}
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        for name in required:
            self.assertEqual(cols[name]["notnull"], 1, f"{name} should be NOT NULL")

    def test_optional_fields_allow_null(self) -> None:
        """可选字段允许 NULL。"""
        optional = {"prompt", "model", "provider", "duration_ms"}
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        for name in optional:
            self.assertEqual(cols[name]["notnull"], 0, f"{name} should allow NULL")

    def test_no_source_table_field(self) -> None:
        """不包含 source_table 字段。"""
        cols = {c["name"] for c in _get_assets_columns(self.db_path)}
        self.assertNotIn("source_table", cols)

    def test_no_source_id_field(self) -> None:
        """不包含 source_id 字段。"""
        cols = {c["name"]: c for c in _get_assets_columns(self.db_path)}
        self.assertNotIn("source_id", cols)

    def test_no_tags_field(self) -> None:
        """不包含 tags 字段。"""
        cols = {c["name"] for c in _get_assets_columns(self.db_path)}
        self.assertNotIn("tags", cols)

    def test_no_thumbnail_path_field(self) -> None:
        """不包含 thumbnail_path 字段。"""
        cols = {c["name"] for c in _get_assets_columns(self.db_path)}
        self.assertNotIn("thumbnail_path", cols)


class AssetsCheckConstraintTest(TestCase):
    """验证 assets 表 CHECK 约束。"""

    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self._tmp.name
        self._tmp.close()
        import angemedia_gateway.config as C
        self._orig_db = C.DB_FILE
        try:
            C.DB_FILE = Path(self.db_path)
            init_db()
        finally:
            C.DB_FILE = self._orig_db

    def tearDown(self) -> None:
        import os
        os.unlink(self.db_path)

    def test_valid_storage_area_output(self) -> None:
        """storage_area='output' 合法。"""
        _insert_asset(self.db_path, storage_area="output")

    def test_valid_storage_area_upload(self) -> None:
        """storage_area='upload' 合法。"""
        _insert_asset(self.db_path, id="u-001", storage_area="upload", relative_path="upload.png", url_path="/uploads/upload.png")

    def test_rejects_invalid_storage_area(self) -> None:
        """storage_area 非法值被拒绝。"""
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_asset(self.db_path, storage_area="invalid")

    def test_valid_media_type_image(self) -> None:
        """media_type='image' 合法。"""
        _insert_asset(self.db_path, media_type="image")

    def test_valid_media_type_video(self) -> None:
        """media_type='video' 合法。"""
        _insert_asset(self.db_path, id="v-001", media_type="video", relative_path="video.mp4", url_path="/generated/video.mp4")

    def test_rejects_invalid_media_type(self) -> None:
        """media_type 非法值被拒绝。"""
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_asset(self.db_path, media_type="audio")

    def test_valid_source_generated(self) -> None:
        """source='generated' 合法。"""
        _insert_asset(self.db_path, source="generated")

    def test_valid_source_upload(self) -> None:
        """source='upload' 合法。"""
        _insert_asset(self.db_path, id="s-001", source="upload", relative_path="up.jpg", url_path="/uploads/up.jpg")

    def test_rejects_invalid_source(self) -> None:
        """source 非法值被拒绝。"""
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_asset(self.db_path, source="downloaded")

    def test_duration_ms_null_insert_succeeds(self) -> None:
        """duration_ms 为 NULL 的插入成功。"""
        _insert_asset(self.db_path, id="n-001", duration_ms=None, relative_path="null_dur.png", url_path="/generated/null_dur.png")

    def test_unique_storage_area_relative_path(self) -> None:
        """重复 (storage_area, relative_path) 被 UNIQUE 约束拒绝。"""
        _insert_asset(self.db_path, id="u-001", storage_area="output", relative_path="dup.png", url_path="/generated/dup.png")
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_asset(self.db_path, id="u-002", storage_area="output", relative_path="dup.png", url_path="/generated/dup2.png")
