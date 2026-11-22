"""Append-only, hash-chained audit log.

* vendor_id is never stored: only HMAC-SHA256(salt, vendor_id).
* Raw daily records are never stored: only their count and date span.
* Each line carries the hash of the previous line, so editing or deleting a past
  entry breaks the chain and `verify_chain` reports it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from vendorscore.logging_setup import get_logger

log = get_logger(__name__)
_DEV_SALT = "dev-only-salt-change-me"
GENESIS = "0" * 64


def hash_vendor_id(vendor_id: str) -> str:
    salt = os.environ.get("AUDIT_SALT", _DEV_SALT)
    return hmac.new(salt.encode(), vendor_id.encode(), hashlib.sha256).hexdigest()


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if os.environ.get("AUDIT_SALT") is None:
            log.warning("AUDIT_SALT not set: using a development salt. Set it in production.")

    def _last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return GENESIS
        with open(self.path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            block = min(size, 65536)
            fh.seek(size - block)
            last = fh.read().decode("utf-8", errors="ignore").strip().splitlines()[-1]
        return json.loads(last)["entry_hash"]

    def append(self, event: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "event": event, **payload,
                     "prev_hash": self._last_hash()}
            body = json.dumps(entry, sort_keys=True, ensure_ascii=False)
            entry["entry_hash"] = hashlib.sha256(body.encode()).hexdigest()
            with open(self.path, "a", encoding="utf-8") as fh:  # append only, never rewrite
                fh.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            return entry

    def tail(self, n: int = 50) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(x) for x in lines[-n:]]

    def verify_chain(self) -> tuple[bool, int]:
        """Returns (ok, number_of_entries_checked)."""
        if not self.path.exists():
            return True, 0
        prev = GENESIS
        n = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            e = json.loads(line)
            h = e.pop("entry_hash")
            if e["prev_hash"] != prev:
                return False, n
            if hashlib.sha256(json.dumps(e, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != h:
                return False, n
            prev = h
            n += 1
        return True, n
