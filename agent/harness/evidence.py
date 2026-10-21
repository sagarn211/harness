from datetime import datetime, timezone

from contracts.schemas import Evidence


class EvidenceLedger:
    def __init__(self):
        self._entries: list[Evidence] = []

    def add(self, evidence: Evidence) -> str:
        self._entries.append(evidence)
        return evidence.source_id

    def all(self) -> list[Evidence]:
        return list(self._entries)


def detect_untrusted_instructions(text: str) -> list[str]:
    phrases = ("skip approval", "ignore policy", "auto-approve", "bypass approval")
    lowered = text.lower()
    return [phrase for phrase in phrases if phrase in lowered]