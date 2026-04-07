from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional


def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(base_dir: str, filename: str, payload: Dict[str, Any]) -> None:
    """
    Convenience helper used by application code.
    Writes a single JSON object per line under `base_dir/filename`.
    """
    ledger = JsonlLedger(base_dir=base_dir)
    path = os.path.join(ledger.base_dir, filename)
    ledger.append(path, payload)


class JsonlLedger:
    """
    Minimal JSONL ledger for iterative runs.
    Each line is a single JSON object to support append-only writes.
    """

    def __init__(self, base_dir: str = "runs") -> None:
        self.base_dir = base_dir
        _ensure_dir(self.base_dir)

    @property
    def tickets_path(self) -> str:
        return os.path.join(self.base_dir, "trade_tickets.jsonl")

    @property
    def paper_fills_path(self) -> str:
        return os.path.join(self.base_dir, "paper_fills.jsonl")

    def append(self, path: str, record: Dict[str, Any]) -> None:
        _ensure_dir(os.path.dirname(path) or ".")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True))
            f.write("\n")

    def record_ticket(self, ticket: Any) -> None:
        payload = ticket.model_dump() if hasattr(ticket, "model_dump") else dict(ticket)
        record = {"timestamp": _now_iso(), "type": "trade_ticket", "payload": payload}
        self.append(self.tickets_path, record)

    def record_paper_fill(self, fill: Dict[str, Any]) -> None:
        record = {"timestamp": _now_iso(), "type": "paper_fill", "payload": fill}
        self.append(self.paper_fills_path, record)

    def iter_jsonl(self, path: str) -> Iterable[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return records


def summarize_recent_tickets(base_dir: str = "runs", limit: int = 20) -> Dict[str, Any]:
    ledger = JsonlLedger(base_dir=base_dir)
    records = list(ledger.iter_jsonl(ledger.tickets_path))
    records = records[-limit:]
    statuses: Dict[str, int] = {}
    modes: Dict[str, int] = {}
    for r in records:
        payload = r.get("payload", {})
        mode = payload.get("mode")
        if mode:
            modes[mode] = modes.get(mode, 0) + 1
        result = payload.get("result") or {}
        status = result.get("status")
        if status:
            statuses[status] = statuses.get(status, 0) + 1
    return {"count": len(records), "modes": modes, "statuses": statuses}
