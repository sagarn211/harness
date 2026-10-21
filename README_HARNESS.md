# Harness Milestone

The state machine moves from `received` through detection, explanation, documentation proposal, human review, formatting, and delivery. `detected`, `explained`, `approved`, and `delivered` are independent statuses; delivery means the harness produced Markdown, not that code was executed or deployed.

Approval binds to the canonical `output_hash` of the exact proposed language, explanation, and documentation. CE-TC3 verifies that editing either field changes the hash and makes the prior approval stale.

Snippet comments and strings are data, never instructions to the harness. CE-TC4 verifies that injection-like phrases are recorded as untrusted evidence while review remains pending.

The `Explainer` Protocol separates orchestration from its implementation. `agent.factory.create_agent()` wires the real `GeminiExplainer` into the harness; the existing `StubExplainer` remains available for offline tests. Gemini requests happen only when `run_analysis()` is called.

Activate the existing virtual environment and set the key in the current PowerShell session:

```powershell
.venv\Scripts\Activate.ps1
$env:GEMINI_API_KEY = "your Gemini API key"
```

Create a wired agent with `from agent.factory import create_agent` and `create_agent("request-id")`. The key is read from `GEMINI_API_KEY`; it is not stored in the repository.

Run tests with:

```bash
PYTHONPATH=. pytest tests/unit tests/scenarios -q
```