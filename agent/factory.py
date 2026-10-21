from agent.harness.evidence import EvidenceLedger
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.gemini_explainer import GeminiExplainer
from agent.tools.language_detect import detect_language


def create_agent(request_id: str, *, api_key: str | None = None) -> Orchestrator:
    return Orchestrator(
        sm=StateMachine(request_id),
        ledger=EvidenceLedger(),
        detect_language_fn=detect_language,
        explainer=GeminiExplainer(api_key=api_key),
    )