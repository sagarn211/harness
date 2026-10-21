import hashlib
import json

from contracts.schemas import WorkflowEvent


def event_fingerprint(event: WorkflowEvent, prev_hash: str) -> str:
    payload = {
        "seq": event.seq,
        "state": event.state,
        "at": event.at.isoformat(),
        "detail": event.detail,
        "prev_hash": prev_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class ChainedEventLog:
    def __init__(self):
        self._events: list[tuple[WorkflowEvent, str]] = []
        self._last_hash: str = "GENESIS"

    def append(self, event: WorkflowEvent) -> str:
        fingerprint = event_fingerprint(event, self._last_hash)
        self._events.append((event, fingerprint))
        self._last_hash = fingerprint
        return fingerprint

    def verify(self) -> tuple[bool, str]:
        previous_hash = "GENESIS"
        for event, stored_fingerprint in self._events:
            expected_fingerprint = event_fingerprint(event, previous_hash)
            if expected_fingerprint != stored_fingerprint:
                return False, f"broken_at_seq_{event.seq}"
            previous_hash = expected_fingerprint
        return True, "ok"

    def events(self) -> list[WorkflowEvent]:
        return [event for event, _ in self._events]