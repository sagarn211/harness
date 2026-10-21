from datetime import datetime, timezone
from enum import Enum

from contracts.schemas import WorkflowEvent
from agent.harness.event_chain import ChainedEventLog


class WorkflowState(str, Enum):
    RECEIVED = "received"
    DETECTING = "detecting"
    EXPLAINING = "explaining"
    PROPOSING_DOCS = "proposing_docs"
    AWAITING_REVIEW = "awaiting_review"
    FORMATTING = "formatting"
    DELIVERED = "delivered"
    NEEDS_INPUT = "needs_input"
    REJECTED = "rejected"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.RECEIVED: {
        WorkflowState.DETECTING,
        WorkflowState.NEEDS_INPUT,
        WorkflowState.CANCELLED,
        WorkflowState.FAILED,
    },
    WorkflowState.DETECTING: {
        WorkflowState.EXPLAINING,
        WorkflowState.FAILED,
        WorkflowState.NEEDS_INPUT,
    },
    WorkflowState.EXPLAINING: {
        WorkflowState.PROPOSING_DOCS,
        WorkflowState.FAILED,
    },
    WorkflowState.PROPOSING_DOCS: {
        WorkflowState.AWAITING_REVIEW,
        WorkflowState.FAILED,
    },
    WorkflowState.AWAITING_REVIEW: {
        WorkflowState.FORMATTING,
        WorkflowState.REJECTED,
        WorkflowState.CANCELLED,
    },
    WorkflowState.FORMATTING: {
        WorkflowState.DELIVERED,
        WorkflowState.FAILED,
    },
    WorkflowState.DELIVERED: set(),
    WorkflowState.NEEDS_INPUT: set(),
    WorkflowState.REJECTED: set(),
    WorkflowState.FAILED: set(),
    WorkflowState.CANCELLED: set(),
}


class IllegalTransition(Exception):
    pass


class StateMachine:
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.current = WorkflowState.RECEIVED
        self.events = [
            WorkflowEvent(
                seq=1,
                request_id=request_id,
                state=self.current.value,
                at=datetime.now(timezone.utc),
            )
        ]
        self.event_chain: ChainedEventLog | None = None

    def transition(
        self,
        to: WorkflowState,
        detail: dict | None = None,
    ) -> None:
        if to not in ALLOWED.get(self.current, set()):
            raise IllegalTransition(f"Cannot transition from {self.current.value} to {to}")

        self.events.append(
            WorkflowEvent(
                seq=len(self.events) + 1,
                request_id=self.request_id,
                state=to.value,
                at=datetime.now(timezone.utc),
                detail={} if detail is None else detail,
            )
        )
        if self.event_chain is not None:
            self.event_chain.append(self.events[-1])
        self.current = to

    def verify_chain(self) -> tuple[bool, str]:
        if self.event_chain is None:
            return (False, "no_chain_attached")
        return self.event_chain.verify()