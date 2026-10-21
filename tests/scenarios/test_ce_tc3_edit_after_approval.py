from datetime import datetime, timezone

import pytest

from agent.harness.approval import StaleApproval, apply_edits
from agent.harness.evidence import EvidenceLedger
from agent.harness.hashing import canonical_output_hash
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.explainer import StubExplainer
from agent.tools.language_detect import detect_language
from contracts.schemas import Approval, CodeSnippet


def test_ce_tc3_edit_after_approval_stales_hash():
    machine = StateMachine("ce-tc3")
    orchestrator = Orchestrator(machine, EvidenceLedger(), detect_language, StubExplainer())
    snippet = CodeSnippet(
        code="def add(a, b): return a + b",
        source_id="source-ce-tc3",
        submitted_at=datetime.now(timezone.utc),
    )
    proposal = orchestrator.run_analysis(snippet)
    assert proposal is not None
    approval = Approval(
        proposal_hash=canonical_output_hash(
            proposal.language,
            proposal.explanation,
            proposal.documentation,
        ),
        approver_id="human-reviewer",
        approved_at=datetime.now(timezone.utc),
        decision="approve",
        edited_explanation="A changed explanation invalidates approval.",
    )

    orchestrator.apply_review(
        proposal,
        approval.model_copy(update={"edited_explanation": None}),
    )
    new_proposal = apply_edits(proposal, approval)

    assert new_proposal.output_hash != proposal.output_hash
    with pytest.raises(StaleApproval):
        orchestrator.format_output(new_proposal, approval)