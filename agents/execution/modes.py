from __future__ import annotations

from enum import Enum


class ExecutionMode(str, Enum):
    DRY_RUN = "dry_run"
    PAPER = "paper"
    LIVE = "live"
