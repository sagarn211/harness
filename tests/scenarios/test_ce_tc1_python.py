from datetime import datetime, timezone

from agent.harness.evidence import EvidenceLedger
from agent.harness.hashing import canonical_output_hash
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.explainer import StubExplainer
from agent.tools.language_detect import detect_language
from contracts.schemas import Approval, CodeSnippet


def test_ce_tc1_python_full_happy_path():
    machine = StateMachine("ce-tc1")
    orchestrator = Orchestrator(machine, EvidenceLedger(), detect_language, StubExplainer())
    snippet = CodeSnippet(
        code="def add(a, b): return a + b",
        source_id="source-ce-tc1",
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

    orchestrator.apply_review(proposal, approval)
    result = orchestrator.format_output(proposal, approval)

    assert result.four_statuses == {
        "detected": True,
        "explained": True,
        "approved": True,
        "delivered": True,
    }
    assert "# Python Snippet" in result.formatted_markdown