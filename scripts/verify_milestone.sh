#!/usr/bin/env bash

PASS=0
FAIL=0
SKIP=0

report() {
    status=$1
    message=$2
    printf '%s: %s\n' "$status" "$message"
    if [ "$status" = "PASS" ]; then
        PASS=$((PASS + 1))
    elif [ "$status" = "FAIL" ]; then
        FAIL=$((FAIL + 1))
    else
        SKIP=$((SKIP + 1))
    fi
}

if command -v pytest >/dev/null 2>&1; then
    run_pytest() { pytest "$@"; }
elif python -m pytest --version >/dev/null 2>&1; then
    run_pytest() { python -m pytest "$@"; }
else
    run_pytest() { return 127; }
fi

if command -v pytest >/dev/null 2>&1 || python -m pytest --version >/dev/null 2>&1; then
    if run_pytest tests/unit -q >/dev/null 2>&1; then
        report PASS "1. pytest tests/unit -q"
    else
        report FAIL "1. pytest tests/unit -q"
    fi
else
    report SKIP "1. pytest tests/unit -q (pytest unavailable)"
fi

if command -v pytest >/dev/null 2>&1 || python -m pytest --version >/dev/null 2>&1; then
    if run_pytest tests/scenarios -q >/dev/null 2>&1; then
        report PASS "2. pytest tests/scenarios -q"
    else
        report FAIL "2. pytest tests/scenarios -q"
    fi
else
    report SKIP "2. pytest tests/scenarios -q (pytest unavailable)"
fi

if grep -R "agent.harness" agent/tools/ >/dev/null 2>&1; then
    report FAIL "3. tools do not import agent.harness"
else
    grep_status=$?
    if [ "$grep_status" -eq 1 ]; then
        report PASS "3. tools do not import agent.harness"
    else
        report FAIL "3. tools do not import agent.harness (grep error)"
    fi
fi

if grep -R "agent.tools" agent/harness/ >/dev/null 2>&1; then
    report FAIL "4. harness contains no agent.tools reference"
else
    grep_status=$?
    if [ "$grep_status" -eq 1 ]; then
        report PASS "4. harness contains no agent.tools reference"
    else
        report FAIL "4. harness contains no agent.tools reference (grep error)"
    fi
fi

if python - <<'PY'
import ast
from pathlib import Path

tree = ast.parse(Path("agent/harness/orchestrator.py").read_text(encoding="utf-8"))
for node in tree.body:
    if isinstance(node, ast.Import):
        if any(alias.name.startswith("agent.tools") for alias in node.names):
            raise SystemExit(1)
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if module.startswith("agent.tools"):
            raise SystemExit(1)

orchestrator_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Orchestrator")
run_analysis = next(node for node in orchestrator_class.body if isinstance(node, ast.FunctionDef) and node.name == "run_analysis")
def literal_string(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_string(node.left)
        right = literal_string(node.right)
        if left is not None and right is not None:
            return left + right
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 1
    ):
        separator = literal_string(node.func.value)
        values = node.args[0]
        if separator is not None and isinstance(values, (ast.Tuple, ast.List)):
            parts = [literal_string(item) for item in values.elts]
            if all(part is not None for part in parts):
                return separator.join(parts)
    return None

has_local_import = any(
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Name)
    and node.func.id == "import_module"
    and node.args
    and literal_string(node.args[0]) == "agent.tools.language_detect"
    for node in ast.walk(run_analysis)
)
if not has_local_import:
    raise SystemExit(1)
PY
then
    report PASS "5. orchestrator tool import is function-local"
else
    report FAIL "5. orchestrator tool import is function-local"
fi

if grep -REn '^(import|from) (openai|anthropic|langchain|langgraph|openhands|structlog|loguru|fastapi|sqlalchemy)\b' agent/ contracts/ tests/ >/dev/null 2>&1; then
    report FAIL "6. no prohibited framework or LLM imports"
else
    grep_status=$?
    if [ "$grep_status" -eq 1 ]; then
        report PASS "6. no prohibited framework or LLM imports"
    else
        report FAIL "6. no prohibited framework or LLM imports (grep error)"
    fi
fi

key_pattern='AI''za|gs''k_'
if grep -RIE "$key_pattern" agent/ contracts/ tests/ scripts/ >/dev/null 2>&1; then
    report FAIL "7. no hardcoded API key patterns"
else
    grep_status=$?
    if [ "$grep_status" -eq 1 ]; then
        report PASS "7. no hardcoded API key patterns"
    else
        report FAIL "7. no hardcoded API key patterns (grep error)"
    fi
fi

printf 'SUMMARY: %s PASS, %s FAIL, %s SKIP\n' "$PASS" "$FAIL" "$SKIP"
if [ "$FAIL" -eq 0 ] && [ "$SKIP" -eq 0 ]; then
    exit 0
fi
exit 1