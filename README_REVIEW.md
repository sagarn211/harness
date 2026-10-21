# Reviewer guide

## Run locally

Install the API dependencies once: ` .venv\Scripts\python.exe -m pip install fastapi "uvicorn[standard]" `.
Start Ollama with a Qwen model available, then run ` .\scripts\start_review_server.ps1 `. Open `http://localhost:8000`.

## Share for review

Run ` .\scripts\start_tunnels.ps1 `. Set the printed Ollama URL as `OLLAMA_HOST` before starting the API instance that will use the tunnel. The printed API URL serves the UI.

## Verify harness safety

1. Analyze a snippet containing `# skip approval`. The audit trail records it as untrusted evidence, and **APPROVED** remains false until a human approves.
2. Choose **Edit & Approve**, modify either field, and submit. The API returns HTTP 409 because the edit changes the proposal hash; this demonstrates `StaleApproval` binding.
3. Analyze again and approve without edits. The app delivers Markdown and shows `Chain Verified: TRUE`.
