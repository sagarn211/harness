"""Local web adapter for the existing deterministic snippet harness."""

from __future__ import annotations

import json
import os
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agent.factory import create_agent
from agent.harness.approval import apply_edits, make_approval_receipt
from agent.tools.explainer import ExplainError
from contracts.schemas import Approval, CodeSnippet, ProposedOutput


FRONTEND_DIR = Path(__file__).resolve().parent
MAX_BODY_BYTES = 1_000_000
MAX_SNIPPET_CHARS = 50_000


@dataclass
class WorkflowSession:
    orchestrator: Any
    proposal: ProposedOutput


SESSIONS: dict[str, WorkflowSession] = {}
SESSIONS_LOCK = threading.Lock()


class FrontendHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY")),
                },
            )
            return

        assets = {
            "/": ("index.html", "text/html; charset=utf-8"),
            "/app.js": ("app.js", "text/javascript; charset=utf-8"),
            "/styles.css": ("styles.css", "text/css; charset=utf-8"),
        }
        asset = assets.get(path)
        if asset is None:
            self.send_error(404)
            return
        try:
            content = (FRONTEND_DIR / asset[0]).read_bytes()
        except OSError:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", asset[1])
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._read_json()
            if path == "/api/analyze":
                self._analyze(payload)
            elif path == "/api/review":
                self._review(payload)
            else:
                self._send_json(404, {"error": "Not found."})
        except ValueError as error:
            self._send_json(400, {"error": str(error)})
        except ExplainError as error:
            self._send_json(502, {"error": str(error)})

    def _read_json(self) -> dict[str, Any]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid content length.") from error
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            raise ValueError("Request body must be between 1 byte and 1 MB.")
        try:
            payload = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Request body must be valid JSON.") from error
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object.")
        return payload

    def _analyze(self, payload: dict[str, Any]) -> None:
        code = payload.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Enter a code snippet first.")
        if len(code) >= MAX_SNIPPET_CHARS:
            raise ValueError("Snippet must be under 50,000 characters.")

        request_id = uuid.uuid4().hex
        snippet = CodeSnippet(
            code=code,
            source_id=f"snippet-{request_id}",
            submitted_at=datetime.now(timezone.utc),
        )
        orchestrator = create_agent(request_id)
        proposal = orchestrator.run_analysis(snippet)
        if proposal is None:
            detail = orchestrator.sm.events[-1].detail
            self._send_json(
                422,
                {
                    "request_id": request_id,
                    "state": orchestrator.sm.current.value,
                    "error": detail.get("reason", "The harness could not analyze this snippet."),
                    "events": [event.model_dump(mode="json") for event in orchestrator.sm.events],
                },
            )
            return

        with SESSIONS_LOCK:
            SESSIONS[request_id] = WorkflowSession(orchestrator, proposal)
        self._send_json(
            200,
            {
                "request_id": request_id,
                "state": orchestrator.sm.current.value,
                "proposal": proposal.model_dump(mode="json"),
                "events": [event.model_dump(mode="json") for event in orchestrator.sm.events],
                "untrusted_evidence": [
                    evidence.model_dump(mode="json")
                    for evidence in orchestrator.ledger.all()
                    if evidence.trust == "untrusted"
                ],
            },
        )

    def _review(self, payload: dict[str, Any]) -> None:
        request_id = payload.get("request_id")
        decision = payload.get("decision")
        approver_id = payload.get("approver_id")
        if not isinstance(request_id, str) or not isinstance(approver_id, str) or not approver_id.strip():
            raise ValueError("A request ID and reviewer ID are required.")
        if decision not in {"approve", "reject"}:
            raise ValueError("Choose approve or reject.")

        with SESSIONS_LOCK:
            session = SESSIONS.get(request_id)
            if session is None:
                raise ValueError("This review session was not found. Run analysis again.")
            orchestrator = session.orchestrator
            proposal = session.proposal
            approved_at = datetime.now(timezone.utc)

            if decision == "reject":
                approval = Approval(
                    proposal_hash=proposal.output_hash,
                    approver_id=approver_id,
                    approved_at=approved_at,
                    decision="reject",
                )
                orchestrator.apply_review(proposal, approval)
                response = self._workflow_response(request_id, orchestrator, "rejected")
            else:
                explanation = payload.get("explanation")
                documentation = payload.get("documentation")
                if not isinstance(explanation, str) or not isinstance(documentation, str):
                    raise ValueError("Explanation and documentation must be text.")
                edit = Approval(
                    proposal_hash=proposal.output_hash,
                    approver_id=approver_id,
                    approved_at=approved_at,
                    decision="approve",
                    edited_explanation=explanation,
                    edited_documentation=documentation,
                )
                reviewed_proposal = apply_edits(proposal, edit)
                approval = Approval(
                    proposal_hash=reviewed_proposal.output_hash,
                    approver_id=approver_id,
                    approved_at=approved_at,
                    decision="approve",
                )
                approval = approval.model_copy(
                    update={"approval_receipt_hash": make_approval_receipt(approval)}
                )
                orchestrator.apply_review(reviewed_proposal, approval)
                result = orchestrator.format_output(reviewed_proposal, approval)
                session.proposal = reviewed_proposal
                response = {
                    "request_id": request_id,
                    "state": orchestrator.sm.current.value,
                    "result": result.model_dump(mode="json"),
                    "events": [event.model_dump(mode="json") for event in orchestrator.sm.events],
                }

        self._send_json(200, response)

    @staticmethod
    def _workflow_response(request_id: str, orchestrator: Any, state: str) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "state": state,
            "events": [event.model_dump(mode="json") for event in orchestrator.sm.events],
        }

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        return


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 8000), FrontendHandler)
    print("Snippet Studio ready at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Snippet Studio.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()