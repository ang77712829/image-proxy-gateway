"""Assistant plan repository."""
from __future__ import annotations

from contextlib import closing
from typing import Any

from ..db.connection import db_connect
from ..helpers import now_iso, safe_json


def save_assistant_plan(plan_id: str, original_prompt: str, media_type: str, plan: dict[str, Any]) -> None:
    with closing(db_connect()) as conn:
        conn.execute(
            "INSERT INTO assistant_plans(id,original_prompt,media_type,plan_json,created_at) VALUES(?,?,?,?,?)",
            (plan_id, original_prompt, media_type, safe_json(plan), now_iso()),
        )
