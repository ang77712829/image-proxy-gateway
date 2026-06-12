"""Upload repository."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
from typing import Any, NamedTuple

from .. import config as C
from ..db.connection import db_connect, db_transaction
from ..helpers import safe_unlink_under


def save_upload(row: dict[str, Any]) -> None:
    with closing(db_connect()) as conn:
        conn.execute(
            "INSERT INTO uploads(id,filename,original_filename,role,content_type,url,local_path,created_at) "
            "VALUES(:id,:filename,:original_filename,:role,:content_type,:url,:local_path,:created_at)",
            row,
        )


class DeleteUploadResult(NamedTuple):
    found: bool
    file_deleted: bool
    local_path: str = ""


def delete_upload(upload_id: str) -> DeleteUploadResult:
    with db_transaction(immediate=True) as conn:
        row = conn.execute("SELECT local_path FROM uploads WHERE id = ?", (upload_id,)).fetchone()
        if row is None:
            return DeleteUploadResult(found=False, file_deleted=False)
        conn.execute("DELETE FROM uploads WHERE id = ?", (upload_id,))
    path = str(row["local_path"] or "")
    if not path:
        return DeleteUploadResult(found=True, file_deleted=True, local_path="")
    resolved = Path(path).expanduser().resolve()
    existed = resolved.exists() and resolved.is_file()
    deleted = safe_unlink_under(path, C.UPLOAD_DIR)
    if existed and not deleted:
        return DeleteUploadResult(found=True, file_deleted=False, local_path=path)
    return DeleteUploadResult(found=True, file_deleted=True, local_path=path)
