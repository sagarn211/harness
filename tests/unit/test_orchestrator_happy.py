from datetime import datetime, timezone

from agent.harness.evidence import EvidenceLedger
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine, WorkflowState
from agent.tools.explainer import StubExplainer
from agent.tools.language_detect import detect_language
from contracts.schemas import CodeSnippet


def test_orchestrator_happy_analysis():
    machine = StateMachine("request-happy")
    ledger = EvidenceLedger()
    orchestrator = Orchestrator(machine, ledger, detect_language, StubExplainer())
    snippet = CodeSnippet(
        code="def add(a, b): return a + b",
        source_id="snippet-happy",
        submitted_at=datetime.now(timezone.utc),
    )

    proposal = orchestrator.run_analysis(snippet)

    assert proposal is not None
    assert machine.current == WorkflowState.AWAITING_REVIEW
    assert proposal.language.name == "Python"
    assert proposal.explanation
    assert proposal.documentation
    assert proposal.output_hash
    assert [event.state for event in machine.events] == [
        "received",
        "detecting",
        "explaining",
        "proposing_docs",
        "awaiting_review",
    ]
    assert any(item.trust == "trusted" for item in ledger.all())
    assert any(item.trust == "untrusted" for item in ledger.all())