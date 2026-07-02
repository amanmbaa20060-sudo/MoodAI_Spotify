#!/usr/bin/env python3
"""Backward-compatible alias for scripts/apply_schemas.py."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "apply_schemas.py"), run_name="__main__")
