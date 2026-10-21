"""FastAPI deployment adapter for the deterministic snippet harness."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.harness.approval import StaleApproval, apply_edits, make_approval_receipt
from agent.harness.evidence import EvidenceLedger
from agent.harness.orchestrator import Orchestrator
from agent.harness.state_machine import StateMachine
from agent.tools.explainer import ExplainError
from agent.tools.language_detect import detect_language
from agent.tools.local_explainer import LocalExplainer
from contracts.schemas import Approval, CodeSnippet, ProposedOutput

app = FastAPI(title="Code Snippet Explainer")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
STORE: dict[str, dict[str, Any]] = {}
INDEX = Path(__file__).with_name("static") / "index.html"


class AnalyzeRequest(BaseModel):
    code: str
    source_id: str


class ReviewRequest(BaseModel):
    approver_id: str
    decision: Literal["approve", "reject"]
    edited_explanation: str | None = None
    edited_documentation: str | None = None


def serialize(session: dict[str, Any]) -> dict[str, Any]:
    orchestrator = session["orchestrator"]
    response: dict[str, Any] = {
        "request_id": orchestrator.sm.request_id,
        "state": orchestrator.sm.current.value,
        "proposal": session["proposal"].model_dump(mode="json"),
        "events": [event.model_dump(mode="json") for event in orchestrator.sm.events],
    }
    if session.get("final_result") is not None:
        response["final_result"] = session["final_result"].model_dump(mode="json")
    return response


def get_session(request_id: str) -> dict[str, Any]:
    try:
        return STORE[request_id]
    except KeyError as error:
        raise HTTPException(404, "Session not found") from error


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(INDEX)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "ollama_host": os.getenv("OLLAMA_HOST", "http://localhost:11434")}


@app.post("/api/analyze")
def analyze(body: AnalyzeRequest) -> dict[str, Any]:
    request_id = uuid.uuid4().hex
    explainer = LocalExplainer(host=os.environ["OLLAMA_HOST"]) if os.getenv("OLLAMA_HOST") else LocalExplainer()
    orchestrator = Orchestrator(StateMachine(request_id), EvidenceLedger(), detect_language, explainer)
    try:
        proposal = orchestrator.run_analysis(CodeSnippet(code=body.code, source_id=body.source_id, submitted_at=datetime.now(timezone.utc)))
    except ExplainError as error:
        raise HTTPException(503, str(error)) from error
    if proposal is None:
        reason = orchestrator.sm.events[-1].detail.get("reason", "Analysis failed")
        if orchestrator.sm.current.value == "failed":
            raise HTTPException(503, reason)
        raise HTTPException(422, reason)
    session = {"orchestrator": orchestrator, "proposal": proposal, "approval": None, "final_result": None}
    STORE[request_id] = session
    return serialize(session)


@app.post("/api/{request_id}/review")
def review(request_id: str, body: ReviewRequest) -> dict[str, Any]:
    session = get_session(request_id)
    proposal: ProposedOutput = session["proposal"]
    approval = Approval(proposal_hash=proposal.output_hash, approver_id=body.approver_id, approved_at=datetime.now(timezone.utc), decision=body.decision, edited_explanation=body.edited_explanation, edited_documentation=body.edited_documentation)
    if body.decision == "approve" and (body.edited_explanation is not None or body.edited_documentation is not None):
        # Edits change the canonical output hash; this deliberately demonstrates stale-approval protection.
        session["proposal"] = apply_edits(proposal, approval)
    try:
        session["orchestrator"].apply_review(session["proposal"], approval)
    except StaleApproval as error:
        raise HTTPException(409, str(error)) from error
    session["approval"] = approval.model_copy(update={"approval_receipt_hash": make_approval_receipt(approval)})
    return serialize(session)


@app.post("/api/{request_id}/format")
def format_result(request_id: str) -> dict[str, Any]:
    session = get_session(request_id)
    try:
        final_result = session["orchestrator"].format_output(session["proposal"], session["approval"])
    except StaleApproval as error:
        raise HTTPException(409, str(error)) from error
    except (RuntimeError, ValueError) as error:
        raise HTTPException(400, str(error)) from error
    session["final_result"] = final_result
    return {"markdown": final_result.formatted_markdown, "final_result": final_result.model_dump(mode="json")}


@app.get("/api/{request_id}")
def session_status(request_id: str) -> dict[str, Any]:
    return serialize(get_session(request_id))
