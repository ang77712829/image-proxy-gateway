"""Video task repository."""
from __future__ import annotations

from contextlib import closing
from typing import Any

from ..db.connection import db_connect
from ..helpers import now_iso, safe_json
from ..security import validate_task_id


def upsert_video_task(
    task_id: str,
    prompt: str,
    model: str,
    status: str,
    result: dict[str, Any],
    duration_ms: int = 0,
) -> None:
    task_id = validate_task_id(task_id)
    with closing(db_connect()) as conn:
        conn.execute(
            """
            INSERT INTO video_tasks(task_id,prompt,model,status,video_url,remote_video_url,local_path,raw_json,created_at,updated_at,provider,duration_ms)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(task_id) DO UPDATE SET
                status=excluded.status,
                video_url=excluded.video_url,
                remote_video_url=excluded.remote_video_url,
                local_path=excluded.local_path,
                raw_json=excluded.raw_json,
                provider=excluded.provider,
                duration_ms=excluded.duration_ms,
                updated_at=excluded.updated_at
            """,
            (
                task_id, prompt, model, status,
                str(result.get("video_url") or ""),
                str(result.get("remote_video_url") or ""),
                str(result.get("local_path") or ""),
                safe_json(result), now_iso(), now_iso(), "agnes_video", int(duration_ms or 0),
            ),
        )
