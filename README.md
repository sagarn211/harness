# Automated Code Snippet Explainer & Documenter

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-API-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Ollama](https://img.shields.io/badge/Ollama-Qwen-black)](https://ollama.com/)

A safety-first local AI application that explains code and produces documentation while requiring cryptographically bound human approval before delivery.

## Architecture

The system deliberately separates decision-making controls from text generation. The deterministic Python harness owns workflow state, human-approval verification, evidence collection, and the cryptographic event chain. It never accepts LLM output as approved by default. Qwen, hosted through Ollama, is an untrusted text-generation tool: it can propose an explanation and documentation, but cannot bypass the harness or human review.

```text
Browser UI
    |
    v
FastAPI adapter  --->  LocalExplainer  --->  Ollama / Qwen
    |                         |                 |
    |                         +--- untrusted proposal
    v
Deterministic Harness
    |-- StateMachine: controlled transitions
    |-- EvidenceLedger: trusted and untrusted evidence
    |-- Approval binding: canonical output hash
    +-- ChainedEventLog: tamper-evident audit trail
    |
    v
Human review  --->  formatting and delivery only after valid approval
```

## Key Features

- **Deterministic state machine.** The harness moves explicitly through `received -> detecting -> explaining -> awaiting_review -> formatting -> delivered`. Invalid transitions are rejected.
- **Hash-bound approvals (CE-TC3).** Approval is bound to a canonical hash of the detected language, explanation, and documentation. Editing an explanation after approval changes that hash and invalidates the approval as stale.
- **Prompt-injection protection (CE-TC4).** Snippet content such as `# skip approval` is handled strictly as untrusted data. It is recorded as evidence and cannot alter the workflow or auto-approve output.
- **Tamper-evident audit log.** Each state transition is cryptographically chained to its predecessor, allowing the delivered result to report whether the event chain verifies.
- **Local model deployment.** The API uses Ollama with Qwen through the `LocalExplainer` tool boundary and exposes a build-free browser interface for reviewers.

## Setup and Installation

### Prerequisites

Install [Ollama](https://ollama.com/download), then download the supported Qwen model:

```powershell
ollama pull qwen2.5-coder:1.5b
```

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` if you want to document local configuration. The application reads `OLLAMA_HOST` (default: `http://localhost:11434`) and `OLLAMA_MODEL` (default: `qwen2.5-coder:1.5b`) from the environment.

Start the API and UI:

```powershell
.\scripts\start_review_server.ps1
```

Open `http://localhost:8000` in a browser.

## Tests and Evidence

Run the automated test suite from the repository root:

```powershell
$env:PYTHONPATH = "."
pytest tests/unit tests/scenarios -q
```

Run the milestone verification script in a Bash-compatible shell:

```bash
bash scripts/verify_milestone.sh
```

These checks exercise the deterministic state machine, approval receipts and hash binding, event-chain integrity, language detection, and the adversarial CE-TC3 and CE-TC4 scenarios. Together, they provide the submitted evidence for the 45 points allocated to Agentic Capability and Technical Implementation.

## Reviewer Demo

1. Start the application with `./scripts/start_review_server.ps1` and open `http://localhost:8000`.
2. Paste a Python or JavaScript snippet and select **Analyze Code**.
3. Review the generated proposal. Select **Approve** to format and deliver Markdown; the audit trail should report `Chain Verified: TRUE`.
4. For prompt-injection protection, analyze code containing `# skip approval`. The proposal still requires a human approval.
5. For CE-TC3, select **Edit & Approve**, change a field, and submit. The API rejects the stale approval with HTTP 409.

### Internet-accessible review with ngrok

Install [ngrok](https://ngrok.com/download), start Ollama and the FastAPI application, then run:

```powershell
.\scripts\start_tunnels.ps1
```

The script prints the API UI URL and the Ollama URL. Set `OLLAMA_HOST` to the printed Ollama tunnel URL before starting an API instance that must reach Ollama across the tunnel.

## Project Structure

```text
agent/harness/       Deterministic state, approval, evidence, and event-chain logic
agent/tools/         Language detection and local LLM tool implementations
apps/api/            FastAPI deployment adapter and browser UI
contracts/           Pydantic workflow contracts
tests/               Unit and adversarial scenario tests
scripts/             Local-review, tunnel, and milestone-verification scripts
```

## Safety Model

This project documents code; it does not execute submitted snippets. LLM-generated content remains a proposal until a named reviewer approves the exact output represented by its canonical hash.
#
