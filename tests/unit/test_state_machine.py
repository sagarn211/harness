import pytest

from agent.harness.state_machine import IllegalTransition, StateMachine, WorkflowState


def test_legal_transition_appends_event():
    machine = StateMachine("request-1")
    prior_count = len(machine.events)

    machine.transition(WorkflowState.DETECTING, {"source": "test"})

    assert machine.current == WorkflowState.DETECTING
    assert len(machine.events) == prior_count + 1
    assert machine.events[-1].seq == prior_count + 1
    assert machine.events[-1].state == "detecting"


def test_illegal_transition_raises():
    machine = StateMachine("request-1")
    with pytest.raises(IllegalTransition):
        machine.transition(WorkflowState.DELIVERED)


def test_received_to_awaiting_review_illegal():
    machine = StateMachine("request-1")
    with pytest.raises(IllegalTransition):
        machine.transition(WorkflowState.AWAITING_REVIEW)


def test_awaiting_review_to_delivered_illegal():
    machine = StateMachine("request-1")
    machine.transition(WorkflowState.DETECTING)
    machine.transition(WorkflowState.EXPLAINING)
    machine.transition(WorkflowState.PROPOSING_DOCS)
    machine.transition(WorkflowState.AWAITING_REVIEW)

    with pytest.raises(IllegalTransition):
        machine.transition(WorkflowState.DELIVERED)