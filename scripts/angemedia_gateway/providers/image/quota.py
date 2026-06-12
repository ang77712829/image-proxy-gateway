"""Local quota guard for ModelScope image generation."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date

from ... import config as C

log = logging.getLogger("angemedia-gateway")


class LocalQuota:
    """Protective local ModelScope counter."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.day = date.today().isoformat()
        self.remaining = C.MODELSCOPE_DAILY_LIMIT
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(C.QUOTA_FILE.read_text(encoding="utf-8"))
            if data.get("day") == self.day:
                self.remaining = int(data.get("remaining", C.MODELSCOPE_DAILY_LIMIT))
        except FileNotFoundError:
            pass
        except Exception as exc:
            log.warning("quota state is ignored: %s", exc)

    def _save(self) -> None:
        C.QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
        C.QUOTA_FILE.write_text(
            json.dumps({"day": self.day, "remaining": self.remaining}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    async def available(self) -> bool:
        async with self.lock:
            today = date.today().isoformat()
            if today != self.day:
                self.day = today
                self.remaining = C.MODELSCOPE_DAILY_LIMIT
                self._save()
            return self.remaining > 0

    async def consume_one(self) -> None:
        async with self.lock:
            self.remaining = max(0, self.remaining - 1)
            self._save()

    async def mark_exhausted(self) -> None:
        async with self.lock:
            self.remaining = 0
            self._save()


quota = LocalQuota()
