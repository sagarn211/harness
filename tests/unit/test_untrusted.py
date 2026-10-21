from agent.harness.untrusted import detect_untrusted_instructions


def test_detects_skip_approval():
    assert detect_untrusted_instructions("# skip approval") == ["skip approval"]


def test_detects_ignore_policy():
    assert detect_untrusted_instructions('"IGNORE POLICY"') == ["ignore policy"]


def test_detects_auto_approve():
    assert detect_untrusted_instructions("# AUTO-APPROVE") == ["auto-approve"]


def test_returns_empty_for_clean_text():
    assert detect_untrusted_instructions("def add(a, b): return a + b") == []