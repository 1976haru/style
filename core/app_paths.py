from __future__ import annotations

import sys
from pathlib import Path


def resource_root() -> Path:
    """Read-only application resources for source and PyInstaller builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS")).resolve()
    return Path(__file__).resolve().parents[1]


def executable_root() -> Path:
    """Writable portable root. In desktop builds this is the EXE folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return resource_root()


RESOURCE_ROOT = resource_root()
APP_ROOT = executable_root()
USER_DATA_ROOT = APP_ROOT / "user_data"


def ensure_user_data_root() -> Path:
    USER_DATA_ROOT.mkdir(parents=True, exist_ok=True)
    return USER_DATA_ROOT
