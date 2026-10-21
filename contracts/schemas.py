from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(strict=True)


class CodeSnippet(_StrictModel):
    code: str
    source_id: str
    submitted_at: datetime


class DetectedLanguage(_StrictModel):
    name: str
    confidence: float
    source: Literal["pygments"]


class ProposedOutput(_StrictModel):
    language: DetectedLanguage
    explanation: str
    documentation: str
    output_hash: str


class Approval(_StrictModel):
    proposal_hash: str
    approver_id: str
    approved_at: datetime
    decision: Literal["approve", "reject"]
    edited_explanation: str | None = None
    edited_documentation: str | None = None
    approval_receipt_hash: str = ""


class Evidence(_StrictModel):
    source_id: str
    source_url: str | None
    retrieved_at: datetime
    extracted: dict[str, Any]
    trust: Literal["trusted", "untrusted"]
    note: str = ""


class WorkflowEvent(_StrictModel):
    seq: int
    request_id: str
    state: str
    at: datetime
    detail: dict[str, Any] = {}


class FinalResult(_StrictModel):
    request_id: str
    detected_language: str
    explanation_hash: str
    approved_at: datetime | None
    formatted_markdown: str | None
    four_statuses: dict[str, bool]
    event_chain_verified: bool = False

    @field_validator("four_statuses")
    @classmethod
    def require_exact_status_keys(cls, value: dict[str, bool]) -> dict[str, bool]:
        expected = {"detected", "explained", "approved", "delivered"}
        if set(value) != expected:
            raise ValueError("four_statuses must contain exactly the four workflow statuses")
        return value