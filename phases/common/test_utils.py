"""Helpers for loading phase-specific app packages in tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def load_phase_module(phase_name: str, module: str):
    root = Path(__file__).resolve().parents[2]
    phase_dir = root / "phases" / phase_name
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    for path in (str(root), str(phase_dir)):
        if path in sys.path:
            sys.path.remove(path)
        sys.path.insert(0, path)
    return importlib.import_module(module)
