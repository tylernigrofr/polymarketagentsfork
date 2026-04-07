from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class TradeSummary:
    total: int
    statuses: Dict[str, int]
    by_mode: Dict[str, int]
    rejected: int


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def summarize_tickets(runs_dir: str = "runs", limit: int = 100) -> TradeSummary:
    path = Path(runs_dir) / "trade_tickets.jsonl"
    rows: List[Dict[str, Any]] = list(_iter_jsonl(path))
    if limit > 0:
        rows = rows[-limit:]

    statuses: Dict[str, int] = {}
    by_mode: Dict[str, int] = {}
    rejected = 0

    for row in rows:
        result = row.get("result") or {}
        status = str(result.get("status") or "UNKNOWN")
        statuses[status] = statuses.get(status, 0) + 1

        mode = str(row.get("mode") or "unknown")
        by_mode[mode] = by_mode.get(mode, 0) + 1

        if status == "REJECTED":
            rejected += 1

    return TradeSummary(
        total=len(rows),
        statuses=statuses,
        by_mode=by_mode,
        rejected=rejected,
    )


def summarize_ledger(runs_dir: str = "runs", limit: int = 100) -> Dict[str, Any]:
    s = summarize_tickets(runs_dir=runs_dir, limit=limit)
    return {
        "total": s.total,
        "statuses": s.statuses,
        "by_mode": s.by_mode,
        "rejected": s.rejected,
    }
