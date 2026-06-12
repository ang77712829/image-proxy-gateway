"""Small table listing helpers for admin/storage read paths."""
from __future__ import annotations

from contextlib import closing
from typing import Any

from fastapi import HTTPException

from ..db.connection import db_connect


TABLE_SELECT_SQL = {
    "generations": "SELECT * FROM generations ORDER BY created_at DESC LIMIT ?",
    "video_tasks": "SELECT * FROM video_tasks ORDER BY created_at DESC LIMIT ?",
    "uploads": "SELECT * FROM uploads ORDER BY created_at DESC LIMIT ?",
    "assistant_plans": "SELECT * FROM assistant_plans ORDER BY created_at DESC LIMIT ?",
}


def list_rows(table: str, limit: int = 50) -> list[dict[str, Any]]:
    sql = TABLE_SELECT_SQL.get(table)
    if sql is None:
        raise HTTPException(status_code=400, detail="不支持的表")
    limit = max(1, min(limit, 200))
    with closing(db_connect()) as conn:
        rows = conn.execute(sql, (limit,)).fetchall()
    return [dict(row) for row in rows]
