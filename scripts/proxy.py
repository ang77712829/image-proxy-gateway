#!/usr/bin/env python3
"""兼容入口：转发到新版图片网关入口。"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

GATEWAY_DIR = Path(__file__).resolve().parent / "image-gateway"
sys.path.insert(0, str(GATEWAY_DIR))
runpy.run_path(str(GATEWAY_DIR / "gateway.py"), run_name="__main__")
