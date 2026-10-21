from datetime import datetime, timezone

import pytest

from agent.harness.approval import (
    StaleApproval,
    check_approval,
    make_approval_receipt,
)
from agent.harness.hashing import canonical_output_hash
from contracts.schemas import Approval, DetectedLanguage, ProposedOutput


def make_proposal() -> ProposedOutput:
    language = DetectedLanguage(name="Python", confidence=0.9, source="pygments")
    explanation = "A short explanation."
    documentation = "A documentation suggestion."
    return ProposedOutput(
        language=language,
        explanation=explanation,
        documentation=documentation,
        output_hash=canonical_output_hash(language, explanation, documentation),
    )


def make_approval(proposal: ProposedOutput, receipt_hash: str = "") -> Approval:
    return Approval(
        proposal_hash=proposal.output_hash,
        approver_id="reviewer-1",
        approved_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        decision="approve",
        approval_receipt_hash=receipt_hash,
    )


def test_valid_receipt_passes():
    proposal = make_proposal()
    approval = make_approval(proposal)
    approval = approval.model_copy(
        update={"approval_receipt_hash": make_approval_receipt(approval)}
    )

    check_approval(approval, proposal)


def test_tampered_receipt_raises():
    proposal = make_proposal()
    approval = make_approval(proposal)
    approval = approval.model_copy(
        update={"approval_receipt_hash": make_approval_receipt(approval)}
    )
    approval = approval.model_copy(update={"approval_receipt_hash": "tampered"})

    with pytest.raises(StaleApproval, match="approval_receipt_mismatch"):
        check_approval(approval, proposal)


def test_legacy_empty_receipt_skipped():
    proposal = make_proposal()

    check_approval(make_approval(proposal), proposal)