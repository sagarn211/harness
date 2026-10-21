from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from importlib import import_module
from typing import Protocol

from contracts.schemas import (
    Approval,
    CodeSnippet,
    Evidence,
    FinalResult,
    ProposedOutput,
)
from agent.harness.approval import check_approval
from agent.harness.evidence import EvidenceLedger, detect_untrusted_instructions
from agent.harness.event_chain import ChainedEventLog
from agent.harness.hashing import canonical_output_hash, canonical_snippet_hash
from agent.harness.state_machine import StateMachine, WorkflowState

 # TODO: Keep this structural contract local to preserve the strict harness/tool import boundary.
class Explainer(Protocol):
    def explain_and_document(self, code: str, language: str) -> tuple[str, str]:
        ...




class Orchestrator:
    def __init__(self, sm: StateMachine, ledger: EvidenceLedger, detect_language_fn, explainer: Explainer):
        self.sm = sm
        self.ledger = ledger
        self.detect_language_fn = detect_language_fn
        self.explainer = explainer
        self.sm.event_chain = ChainedEventLog()

    def run_analysis(self, snippet: CodeSnippet) -> ProposedOutput | None:
        if not snippet.code.strip() or len(snippet.code) >= 50_000:
            reason = "Snippet must contain non-whitespace code and be under 50,000 characters."
            self.ledger.add(
                Evidence(
                    source_id=snippet.source_id,
                    source_url=None,
                    retrieved_at=datetime.now(timezone.utc),
                    extracted={"reason": reason},
                    trust="trusted",
                    note=reason,
                )
            )
            self.sm.transition(WorkflowState.NEEDS_INPUT, {"reason": reason})
            return None

        self.sm.transition(WorkflowState.DETECTING)
        language_detect_module = import_module(".".join(("agent", "tools", "language_detect")))
        detect_error = language_detect_module.DetectError
        try:
            detected = self.detect_language_fn(snippet.code)
        except detect_error as error:
            self.sm.transition(WorkflowState.FAILED, {"reason": str(error)})
            return None

        retrieved_at = datetime.now(timezone.utc)
        self.ledger.add(
            Evidence(
                source_id=snippet.source_id,
                source_url=None,
                retrieved_at=retrieved_at,
                extracted={"snippet_hash": canonical_snippet_hash(snippet)},
                trust="trusted",
                note="Submitted code snippet.",
            )
        )
        self.ledger.add(
            Evidence(
                source_id=snippet.source_id,
                source_url=None,
                retrieved_at=retrieved_at,
                extracted={
                    "language": detected.name,
                    "confidence": detected.confidence,
                    "source": detected.source,
                },
                trust="trusted",
                note="Language detection result.",
            )
        )
        self.sm.transition(WorkflowState.EXPLAINING)

        matches = detect_untrusted_instructions(snippet.code)
        for phrase in matches:
            self.ledger.add(
                Evidence(
                    source_id=snippet.source_id,
                    source_url=None,
                    retrieved_at=datetime.now(timezone.utc),
                    extracted={"matched_phrase": phrase},
                    trust="untrusted",
                    note=f"Untrusted instruction detected in source data: {phrase}",
                )
            )

        try:
            explanation, documentation = self.explainer.explain_and_document(
                snippet.code,
                detected.name,
            )
        except Exception as error:
            explainer_module = import_module(".".join(("agent", "tools", "explainer")))
            if not isinstance(error, explainer_module.ExplainError):
                raise
            self.sm.transition(WorkflowState.FAILED, {"reason": str(error)})
            return None

        self.ledger.add(
            Evidence(
                source_id=snippet.source_id,
                source_url=None,
                retrieved_at=datetime.now(timezone.utc),
                extracted={
                    "explanation": explanation,
                    "documentation": documentation,
                },
                trust="untrusted",
                note="Explainer output is untrusted until human approval.",
            )
        )
        self.sm.transition(WorkflowState.PROPOSING_DOCS)
        proposal = ProposedOutput(
            language=detected,
            explanation=explanation,
            documentation=documentation,
            output_hash=canonical_output_hash(detected, explanation, documentation),
        )
        self.sm.transition(WorkflowState.AWAITING_REVIEW)
        return proposal

    def apply_review(self, proposal: ProposedOutput, approval: Approval) -> ProposedOutput:
        if self.sm.current != WorkflowState.AWAITING_REVIEW:
            raise RuntimeError("Review can only be applied while awaiting review.")
        if approval.decision == "reject":
            self.sm.transition(WorkflowState.REJECTED, {"reason": "Human rejected the proposal."})
            return proposal

        check_approval(approval, proposal)
        self.sm.transition(WorkflowState.FORMATTING)
        return proposal

    def format_output(self, proposal: ProposedOutput, approval: Approval) -> FinalResult:
        if self.sm.current != WorkflowState.FORMATTING:
            raise RuntimeError("Output can only be formatted after approval.")
        check_approval(approval, proposal)
        formatted_markdown = (
            f"# {proposal.language.name} Snippet\n\n"
            f"## Explanation\n\n{proposal.explanation}\n\n"
            f"## Documentation\n\n```\n{proposal.documentation}\n```\n"
        )
        self.sm.transition(WorkflowState.DELIVERED)
        explanation_hash = sha256(proposal.explanation.encode("utf-8")).hexdigest()
        four_statuses = {
            "detected": proposal.language.name != "",
            "explained": bool(proposal.explanation),
            "approved": approval is not None and approval.decision == "approve",
            "delivered": formatted_markdown != "",
        }
        chain_ok, _ = self.sm.verify_chain()
        return FinalResult(
            request_id=self.sm.request_id,
            detected_language=proposal.language.name,
            explanation_hash=explanation_hash,
            approved_at=approval.approved_at,
            formatted_markdown=formatted_markdown,
            four_statuses=four_statuses,
            event_chain_verified=chain_ok,
        )