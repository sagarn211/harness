from datetime import datetime, timezone

from agent.harness.evidence import EvidenceLedger
from agent.harness.hashing import canonical_output_hash
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.explainer import StubExplainer
from agent.tools.language_detect import detect_language
from contracts.schemas import Approval, CodeSnippet


def test_ce_tc2_javascript_full_happy_path():
    machine = StateMachine("ce-tc2")
    orchestrator = Orchestrator(machine, EvidenceLedger(), detect_language, StubExplainer())
    snippet = CodeSnippet(
        code="const f = (x) => x + 1;",
        source_id="source-ce-tc2",
        submitted_at=datetime.now(timezone.utc),
    )
    proposal = orchestrator.run_analysis(snippet)
    assert proposal is not None
    assert proposal.language.name == "JavaScript"
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

    assert "# JavaScript Snippet" in result.formatted_markdown