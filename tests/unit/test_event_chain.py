from datetime import datetime, timezone

from agent.harness.event_chain import ChainedEventLog
from agent.harness.state_machine import StateMachine
from contracts.schemas import WorkflowEvent


def make_event(seq: int) -> WorkflowEvent:
    return WorkflowEvent(
        seq=seq,
        request_id="chain-test",
        state=f"state-{seq}",
        at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_genesis_chain_starts_clean():
    machine = StateMachine("chain-test")
    chain = ChainedEventLog()
    chain.append(machine.events[0])

    assert chain.verify() == (True, "ok")


def test_tamper_breaks_chain():
    chain = ChainedEventLog()
    for seq in range(1, 4):
        chain.append(make_event(seq))

    chain._events[1][0].state = "tampered"

    assert chain.verify() == (False, "broken_at_seq_2")


def test_chain_detects_deleted_event():
    chain = ChainedEventLog()
    for seq in range(1, 4):
        chain.append(make_event(seq))
    chain._events.pop(1)

    valid, detail = chain.verify()

    assert valid is False
    assert detail.startswith("broken_at_seq_")


def test_verify_is_deterministic():
    chain = ChainedEventLog()
    for seq in range(1, 4):
        chain.append(make_event(seq))

    first = chain.verify()
    second = chain.verify()

    assert first == second == (True, "ok")