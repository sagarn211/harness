import hashlib
import json

from contracts.schemas import Approval, DetectedLanguage, ProposedOutput
from agent.harness.hashing import canonical_output_hash


class StaleApproval(Exception):
    pass


class MissingApproval(Exception):
    pass


def make_approval_receipt(approval: Approval) -> str:
    payload = {
        "proposal_hash": approval.proposal_hash,
        "approver_id": approval.approver_id,
        "approved_at": approval.approved_at.isoformat(),
        "decision": approval.decision,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def check_approval(
    approval: Approval | None,
    current_output: ProposedOutput,
) -> None:
    if approval is None or approval.decision != "approve":
        raise MissingApproval("A human approval is required.")

    expected_hash = canonical_output_hash(
        current_output.language,
        current_output.explanation,
        current_output.documentation,
    )
    if approval.proposal_hash != expected_hash:
        raise StaleApproval("Approval does not match the current proposed output.")
    if approval.approval_receipt_hash:
        expected_receipt = make_approval_receipt(approval)
        if approval.approval_receipt_hash != expected_receipt:
            raise StaleApproval("approval_receipt_mismatch")


def apply_edits(proposal: ProposedOutput, approval: Approval) -> ProposedOutput:
    if approval.edited_explanation is None and approval.edited_documentation is None:
        return proposal

    explanation = (
        proposal.explanation
        if approval.edited_explanation is None
        else approval.edited_explanation
    )
    documentation = (
        proposal.documentation
        if approval.edited_documentation is None
        else approval.edited_documentation
    )
    output_hash = canonical_output_hash(
        proposal.language,
        explanation,
        documentation,
    )
    return ProposedOutput(
        language=proposal.language,
        explanation=explanation,
        documentation=documentation,
        output_hash=output_hash,
    )