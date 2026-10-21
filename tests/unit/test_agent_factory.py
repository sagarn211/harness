from agent import factory
from agent.harness.orchestrator import Orchestrator
from agent.tools.language_detect import detect_language


def test_create_agent_wires_gemini_explainer(monkeypatch):
    explainer = object()
    monkeypatch.setattr(factory, "GeminiExplainer", lambda api_key=None: explainer)

    orchestrator = factory.create_agent("factory-test")

    assert isinstance(orchestrator, Orchestrator)
    assert orchestrator.sm.request_id == "factory-test"
    assert orchestrator.detect_language_fn is detect_language
    assert orchestrator.explainer is explainer
    assert orchestrator.sm.event_chain is not None