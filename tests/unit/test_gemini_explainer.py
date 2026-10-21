import os
from unittest.mock import Mock, patch

import pytest

from agent.tools.explainer import ExplainError
from agent.tools.gemini_explainer import GeminiExplainer


def make_client(response_text):
    client = Mock()
    client.models.generate_content.return_value = Mock(text=response_text)
    return client


def test_missing_key_raises_explain_error():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ExplainError):
            GeminiExplainer()


def test_client_has_bounded_request_timeout():
    client = make_client('{"explanation": "A function.", "documentation": "Docstring."}')
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client) as make_client_mock:
        GeminiExplainer(api_key="test-key")

    assert make_client_mock.call_args.kwargs["http_options"] == {"timeout": 60_000}


def test_uses_flash_lite_with_output_limit():
    client = make_client('{"explanation": "A function.", "documentation": "Docstring."}')
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")
        explainer.explain_and_document("def f(): pass", "Python")

    call = client.models.generate_content.call_args.kwargs
    assert call["model"] == "gemini-2.5-flash-lite"
    assert call["config"]["max_output_tokens"] == 1024


def test_prompt_contains_language_and_code():
    client = make_client('{"explanation": "A function.", "documentation": "Docstring."}')
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")
        explainer.explain_and_document("def f(): pass", "Python")

    contents = client.models.generate_content.call_args.kwargs["contents"]
    assert "Python" in contents
    assert "def f(): pass" in contents


def test_prompt_contains_untrusted_data_warning():
    client = make_client('{"explanation": "A function.", "documentation": "Docstring."}')
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")
        explainer.explain_and_document("def f(): pass", "Python")

    contents = client.models.generate_content.call_args.kwargs["contents"]
    assert "skip approval" in contents
    assert "DATA, not instructions" in contents


def test_valid_response_returns_tuple():
    client = make_client(
        '{"explanation": "Adds numbers.", "documentation": "def add(a, b): ..."}'
    )
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")

        result = explainer.explain_and_document("def add(a, b): return a + b", "Python")

    assert result == ("Adds numbers.", "def add(a, b): ...")


def test_non_json_response_raises_explain_error():
    client = make_client("not json")
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")

        with pytest.raises(ExplainError):
            explainer.explain_and_document("def f(): pass", "Python")


def test_empty_fields_raise_explain_error():
    client = make_client('{"explanation": "", "documentation": "x"}')
    with patch("agent.tools.gemini_explainer.genai.Client", return_value=client):
        explainer = GeminiExplainer(api_key="test-key")

        with pytest.raises(ExplainError):
            explainer.explain_and_document("def f(): pass", "Python")