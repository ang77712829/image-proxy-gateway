"""gateway_api_keys 表 + state 层 CRUD 测试。"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from angemedia_gateway.state import init_db


class _GatewayKeyTestBase(unittest.TestCase):
    """共享 setUp/tearDown：独立临时目录 + 临时 DB。"""

    def setUp(self) -> None:
        self._tmp_dir = tempfile.mkdtemp(prefix="gateway-key-test-")
        self.db_path = Path(self._tmp_dir) / "test.db"
        import angemedia_gateway.config as C
        self._orig_db = C.DB_FILE
        self._config_mod = C
        C.DB_FILE = self.db_path
        init_db()

    def tearDown(self) -> None:
        self._config_mod.DB_FILE = self._orig_db
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn


# ── 1. 表存在与迁移记录 ────────────────────────────────

class GatewayKeysTableTest(_GatewayKeyTestBase):
    """gateway_api_keys 表存在且迁移已记录。"""

    def test_table_exists(self) -> None:
        """init_db() 创建 gateway_api_keys 表。"""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='gateway_api_keys'"
            ).fetchone()
            self.assertIsNotNone(row)
        finally:
            conn.close()

    def test_migration_record_exists(self) -> None:
        """schema_migrations 包含 gateway_api_keys_v1 记录。"""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM schema_migrations WHERE version = 'gateway_api_keys_v1'"
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertIn("T", row["applied_at"])
        finally:
            conn.close()

    def test_table_has_10_columns(self) -> None:
        """gateway_api_keys 表有 10 个字段。"""
        conn = self._conn()
        try:
            cols = conn.execute("PRAGMA table_info(gateway_api_keys)").fetchall()
            self.assertEqual(len(cols), 10)
        finally:
            conn.close()


# ── 2. create_gateway_api_key ──────────────────────────

class CreateGatewayKeyTest(_GatewayKeyTestBase):
    """create_gateway_api_key 函数。"""

    def test_create_returns_key(self) -> None:
        """创建返回 key 字段，am- 前缀，full_key 不暴露。"""
        from angemedia_gateway.state import create_gateway_api_key
        result = create_gateway_api_key(name="test-key")
        self.assertIn("key", result)
        self.assertTrue(result["key"].startswith("am-"))
        self.assertNotIn("full_key", result)
        self.assertNotIn("key_hash", result)

    def test_create_key_is_unique(self) -> None:
        """两次创建产生不同的 key。"""
        from angemedia_gateway.state import create_gateway_api_key
        r1 = create_gateway_api_key()
        r2 = create_gateway_api_key()
        self.assertNotEqual(r1["key"], r2["key"])

    def test_create_default_fields(self) -> None:
        """创建后 enabled=True, last_used_at=None, revoked_at=None。"""
        from angemedia_gateway.state import create_gateway_api_key
        result = create_gateway_api_key(name="default-test")
        self.assertTrue(result["enabled"])
        self.assertIsNone(result["last_used_at"])
        self.assertIsNone(result["revoked_at"])
        self.assertEqual(result["name"], "default-test")

    def test_create_with_note(self) -> None:
        """note 参数写入记录。"""
        from angemedia_gateway.state import create_gateway_api_key
        result = create_gateway_api_key(name="noted", note="for testing")
        self.assertEqual(result["note"], "for testing")

    def test_create_stores_hash_in_db(self) -> None:
        """创建后 DB 中 key_hash 不为空（直接查询 DB 验证）。"""
        from angemedia_gateway.state import create_gateway_api_key
        from angemedia_gateway.security import hash_token
        result = create_gateway_api_key(name="hash-check")
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT key_hash FROM gateway_api_keys WHERE id = ?",
                (result["id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["key_hash"], hash_token(result["key"]))
        finally:
            conn.close()


# ── 3. list_gateway_api_keys ───────────────────────────

class ListGatewayKeysTest(_GatewayKeyTestBase):
    """list_gateway_api_keys 函数。"""

    def test_list_empty_by_default(self) -> None:
        """空表返回空列表。"""
        from angemedia_gateway.state import list_gateway_api_keys
        self.assertEqual(list_gateway_api_keys(), [])

    def test_list_excludes_key_hash_and_full_key(self) -> None:
        """列表不含 key_hash 和 key（full_key）字段。"""
        from angemedia_gateway.state import create_gateway_api_key, list_gateway_api_keys
        create_gateway_api_key(name="no-hash")
        keys = list_gateway_api_keys()
        self.assertEqual(len(keys), 1)
        self.assertNotIn("key_hash", keys[0])
        self.assertNotIn("key", keys[0])

    def test_list_returns_created_key(self) -> None:
        """创建后列表包含该 key 的 name。"""
        from angemedia_gateway.state import create_gateway_api_key, list_gateway_api_keys
        create_gateway_api_key(name="listed")
        keys = list_gateway_api_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["name"], "listed")
        self.assertTrue(keys[0]["enabled"])


# ── 4. get_gateway_api_key ─────────────────────────────

class GetGatewayKeyTest(_GatewayKeyTestBase):
    """get_gateway_api_key 函数。"""

    def test_get_existing_key(self) -> None:
        """按 ID 查询返回完整记录（不含 key_hash 和 key）。"""
        from angemedia_gateway.state import create_gateway_api_key, get_gateway_api_key
        created = create_gateway_api_key(name="get-me")
        fetched = get_gateway_api_key(created["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "get-me")
        self.assertEqual(fetched["id"], created["id"])
        self.assertNotIn("key_hash", fetched)
        self.assertNotIn("key", fetched)

    def test_get_nonexistent_returns_none(self) -> None:
        """不存在的 ID 返回 None。"""
        from angemedia_gateway.state import get_gateway_api_key
        self.assertIsNone(get_gateway_api_key("nonexistent-id"))

    def test_get_excludes_key_hash(self) -> None:
        """get 不返回 key_hash（通过 DB 对比验证）。"""
        from angemedia_gateway.state import create_gateway_api_key, get_gateway_api_key
        created = create_gateway_api_key()
        fetched = get_gateway_api_key(created["id"])
        self.assertIsNotNone(fetched)
        self.assertNotIn("key_hash", fetched)
        # DB 中确实有 key_hash
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT key_hash FROM gateway_api_keys WHERE id = ?",
                (created["id"],),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertTrue(len(row["key_hash"]) > 0)
        finally:
            conn.close()


# ── 5. update_gateway_api_key ──────────────────────────

class UpdateGatewayKeyTest(_GatewayKeyTestBase):
    """update_gateway_api_key 函数。"""

    def test_update_name(self) -> None:
        """更新 name 字段。"""
        from angemedia_gateway.state import create_gateway_api_key, update_gateway_api_key
        created = create_gateway_api_key(name="old-name")
        updated = update_gateway_api_key(created["id"], name="new-name")
        self.assertIsNotNone(updated)
        self.assertEqual(updated["name"], "new-name")

    def test_update_enabled(self) -> None:
        """禁用 key。"""
        from angemedia_gateway.state import create_gateway_api_key, update_gateway_api_key
        created = create_gateway_api_key()
        self.assertTrue(created["enabled"])
        updated = update_gateway_api_key(created["id"], enabled=False)
        self.assertIsNotNone(updated)
        self.assertFalse(updated["enabled"])

    def test_update_nonexistent_returns_none(self) -> None:
        """更新不存在的 ID 返回 None。"""
        from angemedia_gateway.state import update_gateway_api_key
        self.assertIsNone(update_gateway_api_key("fake-id", name="x"))


# ── 6. revoke_gateway_api_key ──────────────────────────

class RevokeGatewayKeyTest(_GatewayKeyTestBase):
    """revoke_gateway_api_key 函数。"""

    def test_revoke_sets_revoked_at(self) -> None:
        """吊销后 revoked_at 不为 None。"""
        from angemedia_gateway.state import create_gateway_api_key, revoke_gateway_api_key, get_gateway_api_key
        created = create_gateway_api_key()
        result = revoke_gateway_api_key(created["id"])
        self.assertTrue(result)
        fetched = get_gateway_api_key(created["id"])
        self.assertIsNotNone(fetched)
        self.assertIsNotNone(fetched["revoked_at"])

    def test_revoke_nonexistent_returns_false(self) -> None:
        """吊销不存在的 ID 返回 False。"""
        from angemedia_gateway.state import revoke_gateway_api_key
        self.assertFalse(revoke_gateway_api_key("fake-id"))

    def test_double_revoke_returns_false(self) -> None:
        """重复吊销同一只返回第一次 True，第二次 False。"""
        from angemedia_gateway.state import create_gateway_api_key, revoke_gateway_api_key
        created = create_gateway_api_key()
        self.assertTrue(revoke_gateway_api_key(created["id"]))
        self.assertFalse(revoke_gateway_api_key(created["id"]))


# ── 7. verify_gateway_api_key ──────────────────────────

class VerifyGatewayKeyTest(_GatewayKeyTestBase):
    """verify_gateway_api_key 函数。"""

    def test_verify_valid_key(self) -> None:
        """用 key 验证返回 key 记录（不含 key_hash）。"""
        from angemedia_gateway.state import create_gateway_api_key, verify_gateway_api_key
        created = create_gateway_api_key(name="verify-me")
        result = verify_gateway_api_key(created["key"])
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], created["id"])
        self.assertEqual(result["name"], "verify-me")
        self.assertNotIn("key_hash", result)
        self.assertNotIn("key", result)

    def test_verify_disabled_key_returns_none(self) -> None:
        """禁用的 key 验证失败。"""
        from angemedia_gateway.state import (
            create_gateway_api_key, update_gateway_api_key, verify_gateway_api_key,
        )
        created = create_gateway_api_key()
        update_gateway_api_key(created["id"], enabled=False)
        self.assertIsNone(verify_gateway_api_key(created["key"]))

    def test_verify_revoked_key_returns_none(self) -> None:
        """已吊销的 key 验证失败。"""
        from angemedia_gateway.state import create_gateway_api_key, revoke_gateway_api_key, verify_gateway_api_key
        created = create_gateway_api_key()
        revoke_gateway_api_key(created["id"])
        self.assertIsNone(verify_gateway_api_key(created["key"]))

    def test_verify_wrong_key_returns_none(self) -> None:
        """错误的 key 验证失败。"""
        from angemedia_gateway.state import create_gateway_api_key, verify_gateway_api_key
        create_gateway_api_key()
        self.assertIsNone(verify_gateway_api_key("am-wrongkey000000000000000000"))

    def test_verify_empty_string_returns_none(self) -> None:
        """空字符串验证返回 None。"""
        from angemedia_gateway.state import verify_gateway_api_key
        self.assertIsNone(verify_gateway_api_key(""))


# ── 8. update_gateway_api_key_last_used ────────────────

class UpdateLastUsedTest(_GatewayKeyTestBase):
    """update_gateway_api_key_last_used 函数。"""

    def test_update_last_used(self) -> None:
        """更新 last_used_at 和 last_used_ip。"""
        from angemedia_gateway.state import (
            create_gateway_api_key, update_gateway_api_key_last_used, get_gateway_api_key,
        )
        created = create_gateway_api_key()
        result = update_gateway_api_key_last_used(created["id"], ip="127.0.0.1")
        self.assertTrue(result)
        fetched = get_gateway_api_key(created["id"])
        self.assertIsNotNone(fetched["last_used_at"])
        self.assertEqual(fetched["last_used_ip"], "127.0.0.1")

    def test_update_last_used_nonexistent_returns_false(self) -> None:
        """不存在的 ID 返回 False。"""
        from angemedia_gateway.state import update_gateway_api_key_last_used
        self.assertFalse(update_gateway_api_key_last_used("fake-id"))

    def test_update_last_used_no_ip(self) -> None:
        """不传 ip 时 last_used_ip 为 None。"""
        from angemedia_gateway.state import (
            create_gateway_api_key, update_gateway_api_key_last_used, get_gateway_api_key,
        )
        created = create_gateway_api_key()
        update_gateway_api_key_last_used(created["id"])
        fetched = get_gateway_api_key(created["id"])
        self.assertIsNotNone(fetched["last_used_at"])
        self.assertIsNone(fetched["last_used_ip"])


# ── 9. idempotent init_db ──────────────────────────────

class GatewayKeysInitDbIdempotentTest(_GatewayKeyTestBase):
    """gateway_api_keys 在重复 init_db() 后不丢失。"""

    def test_table_survives_second_init(self) -> None:
        """第二次 init_db() 后表和数据仍在。"""
        from angemedia_gateway.state import create_gateway_api_key, list_gateway_api_keys
        create_gateway_api_key(name="persist-me")
        init_db()
        keys = list_gateway_api_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["name"], "persist-me")

    def test_migration_not_duplicated(self) -> None:
        """重复 init_db() 后 gateway_api_keys_v1 仍只有一条。"""
        init_db()
        init_db()
        conn = self._conn()
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM schema_migrations WHERE version = 'gateway_api_keys_v1'"
            ).fetchone()[0]
            self.assertEqual(count, 1)
        finally:
            conn.close()


# ── 10. UNIQUE constraint & key_prefix ─────────────────

class GatewayKeysUniqueHashTest(_GatewayKeyTestBase):
    """key_hash UNIQUE 约束与 key_prefix 长度。"""

    def test_different_keys_different_hashes_in_db(self) -> None:
        """不同 key 在 DB 中产生不同 key_hash（直接查询 DB 验证）。"""
        from angemedia_gateway.state import create_gateway_api_key
        r1 = create_gateway_api_key()
        r2 = create_gateway_api_key()
        conn = self._conn()
        try:
            h1 = conn.execute(
                "SELECT key_hash FROM gateway_api_keys WHERE id = ?",
                (r1["id"],),
            ).fetchone()["key_hash"]
            h2 = conn.execute(
                "SELECT key_hash FROM gateway_api_keys WHERE id = ?",
                (r2["id"],),
            ).fetchone()["key_hash"]
            self.assertNotEqual(h1, h2)
        finally:
            conn.close()

    def test_prefix_length_11(self) -> None:
        """key_prefix 为 am- + 8 hex，共 11 字符。"""
        from angemedia_gateway.state import create_gateway_api_key
        result = create_gateway_api_key()
        self.assertEqual(len(result["key_prefix"]), 11)
        self.assertTrue(result["key_prefix"].startswith("am-"))
        self.assertEqual(result["key_prefix"], result["key"][:11])


# ── 11. DB 约束与安全 ─────────────────────────────────

class GatewayKeysDbConstraintTest(_GatewayKeyTestBase):
    """enabled CHECK / key_hash UNIQUE / key 不落库。"""

    def test_enabled_check_rejects_2(self) -> None:
        """直接 SQL 插入 enabled=2 触发 CHECK 约束异常。"""
        conn = self._conn()
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO gateway_api_keys(id,name,key_prefix,key_hash,enabled,created_at) "
                    "VALUES('c1','','aa','hh',2,'2026-01-01T00:00:00+00:00')",
                )
        finally:
            conn.close()

    def test_full_key_not_stored_in_db(self) -> None:
        """create 后完整 key 不出现在任何 DB 字段值中。"""
        from angemedia_gateway.state import create_gateway_api_key
        result = create_gateway_api_key(name="no-leak")
        full_key = result["key"]
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT * FROM gateway_api_keys WHERE id = ?", (result["id"],)
            ).fetchone()
            self.assertIsNotNone(row)
            for col in row.keys():
                val = str(row[col] or "")
                self.assertNotIn(
                    full_key, val,
                    f"完整 key 出现在 DB 字段 {col} 中",
                )
        finally:
            conn.close()

    def test_key_hash_unique_rejects_duplicate(self) -> None:
        """直接 SQL 插入相同 key_hash 触发 UNIQUE 约束异常。"""
        from angemedia_gateway.state import create_gateway_api_key
        created = create_gateway_api_key()
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT key_hash FROM gateway_api_keys WHERE id = ?",
                (created["id"],),
            ).fetchone()
            duplicate_hash = row["key_hash"]
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO gateway_api_keys(id,name,key_prefix,key_hash,enabled,created_at) "
                    "VALUES(?,?,?,?,1,?)",
                    ("dup-id", "dup", "dup", duplicate_hash, "2026-01-01T00:00:00+00:00"),
                )
        finally:
            conn.close()


# ── 12. 旧 config 表 GATEWAY_API_KEY 兼容性 ───────────

class LegacyConfigCompatibilityTest(_GatewayKeyTestBase):
    """新 gateway_api_keys 表不影响旧 config 表中的 GATEWAY_API_KEY。"""

    def test_legacy_config_key_preserved_after_init_and_create(self) -> None:
        """旧 GATEWAY_API_KEY 在 init_db + create_gateway_api_key 后完整保留。"""
        from angemedia_gateway.state import create_gateway_api_key, set_config, get_config
        legacy_value = "am-legacy-test-key-000000000000"
        # 1. 写入旧 config 表（使用 set_config helper）
        set_config("GATEWAY_API_KEY", legacy_value)
        # 确认写入成功
        self.assertEqual(get_config("GATEWAY_API_KEY"), legacy_value)
        # 2. init_db()
        init_db()
        # 3. 创建新多 key
        new_result = create_gateway_api_key(name="new-multi-key")
        # 4. 旧 config 表中的值仍然存在且不变
        self.assertEqual(get_config("GATEWAY_API_KEY"), legacy_value)
        # 5. gateway_api_keys 表中有新 key
        conn = self._conn()
        try:
            new_count = conn.execute(
                "SELECT COUNT(*) FROM gateway_api_keys WHERE name = 'new-multi-key'"
            ).fetchone()[0]
            self.assertEqual(new_count, 1)
            # 6. 旧 key 没有被迁移/复制到 gateway_api_keys 表
            from angemedia_gateway.security import hash_token
            legacy_hash = hash_token(legacy_value)
            legacy_in_keys = conn.execute(
                "SELECT COUNT(*) FROM gateway_api_keys WHERE key_hash = ?",
                (legacy_hash,),
            ).fetchone()[0]
            self.assertEqual(legacy_in_keys, 0)
        finally:
            conn.close()
