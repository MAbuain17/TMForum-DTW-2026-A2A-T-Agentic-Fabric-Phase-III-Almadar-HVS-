"""Hash-linked run records for inspecting handoffs and decisions."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json


def digest(record):
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


class AuditLog:
    def __init__(self):
        self._records = []

    def append(self, kind, agent, summary, **details):
        record = {
            "sequence": len(self._records) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "agent": agent,
            "summary": summary,
            "details": deepcopy(details),
            "previous_hash": self._records[-1]["hash"] if self._records else "0" * 64,
        }
        record["hash"] = digest(record)
        self._records.append(record)

    @property
    def records(self):
        return deepcopy(self._records)


def verify_chain(records):
    previous = "0" * 64
    for sequence, original in enumerate(records, start=1):
        record = dict(original)
        claimed = record.pop("hash", None)
        if record.get("sequence") != sequence or record.get("previous_hash") != previous:
            return False
        if digest(record) != claimed:
            return False
        previous = claimed
    return True
