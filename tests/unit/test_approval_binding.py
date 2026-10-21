from datetime import datetime, timezone

import pytest

from agent.harness.approval import (
    MissingApproval,
    StaleApproval,
    apply_edits,
    check_approval,
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


def make_approval(proposal_hash: str, **kwargs) -> Approval:
    return Approval(
        proposal_hash=proposal_hash,
        approver_id="reviewer-1",
        approved_at=datetime.now(timezone.utc),
        decision="approve",
        **kwargs,
    )


def test_matching_hash_passes():
    proposal = make_proposal()
    check_approval(make_approval(proposal.output_hash), proposal)


def test_wrong_hash_raises_stale_approval():
    proposal = make_proposal()
    with pytest.raises(StaleApproval):
        check_approval(make_approval("wrong-hash"), proposal)


def test_missing_approval_raises():
    with pytest.raises(MissingApproval):
        check_approval(None, make_proposal())


def test_reject_decision_raises_missing_approval():
    proposal = make_proposal()
    approval = Approval(
        proposal_hash=proposal.output_hash,
        approver_id="reviewer-1",
        approved_at=datetime.now(timezone.utc),
        decision="reject",
    )
    with pytest.raises(MissingApproval):
        check_approval(approval, proposal)


def test_apply_edits_changes_hash():
    proposal = make_proposal()
    approval = make_approval(
        proposal.output_hash,
        edited_explanation="An edited explanation.",
    )
    edited = apply_edits(proposal, approval)

    assert edited.explanation == "An edited explanation."
    assert edited.output_hash != proposal.output_hash