from datetime import datetime, timezone

from agent.harness.approval import make_approval_receipt
from agent.harness.evidence import EvidenceLedger
from agent.harness.hashing import canonical_output_hash
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.explainer import StubExplainer
from agent.tools.language_detect import detect_language
from contracts.schemas import Approval, CodeSnippet


def test_ce_chain_integrity_full_flow():
    machine = StateMachine("ce-chain-integrity")
    orchestrator = Orchestrator(machine, EvidenceLedger(), detect_language, StubExplainer())
    snippet = CodeSnippet(
        code="def add(a, b): return a + b",
        source_id="source-ce-chain-integrity",
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
    )
    approval = approval.model_copy(
        update={"approval_receipt_hash": make_approval_receipt(approval)}
    )

    orchestrator.apply_review(proposal, approval)
    result = orchestrator.format_output(proposal, approval)

    assert result.event_chain_verified is True
    assert machine.verify_chain() == (True, "ok")