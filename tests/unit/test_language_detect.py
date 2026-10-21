import subprocess
import sys

import pytest


def test_detects_python():
    from agent.tools.language_detect import detect_language

    detected = detect_language("def foo(x): return x + 1")

    assert detected.name == "Python"


def test_detects_javascript():
    from agent.tools.language_detect import detect_language

    detected = detect_language("const f = (x) => x + 1;")

    assert detected.name == "JavaScript"


def test_empty_code_raises_detect_error():
    from agent.tools.language_detect import DetectError, detect_language

    with pytest.raises(DetectError):
        detect_language("")


def test_does_not_import_harness():
    script = (
        "import sys; import agent.tools.language_detect; "
        "print(','.join(name for name in sys.modules if name.startswith('agent.harness')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == "\n"