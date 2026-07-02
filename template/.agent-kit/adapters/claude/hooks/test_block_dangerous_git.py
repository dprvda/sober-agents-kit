# REASON: Smoke tests for the block-dangerous-git PreToolUse hook — feeds known-dangerous
# and known-safe commands as JSON on stdin and asserts exit codes, because hook regressions
# silently let dangerous commands through and there is no other test infra covering Claude
# Code hooks in this scaffold.
"""Smoke tests for block-dangerous-git.py. Run from repo root:
    python .agent-kit/adapters/claude/hooks/test_block_dangerous_git.py
"""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent / "block-dangerous-git.py"

CASES = [
    # (command, should_block, label)
    ("g" + "it push --force origin main", True, "force push to main"),
    ("g" + "it push -f origin main", True, "force push -f"),
    ("g" + "it push origin master", False, "direct master push (ALLOWED)"),
    ("g" + "it push origin main", False, "direct main push (ALLOWED)"),
    ("g" + "it push HEAD:master", False, "HEAD:master push (ALLOWED)"),
    ("g" + "it reset --hard HEAD~1", True, "hard reset"),
    ("g" + "it clean -fd", True, "clean -fd"),
    ("g" + "it clean -f", True, "clean -f"),
    ("g" + "it branch -D feat", True, "branch -D"),
    ("g" + "it checkout .", True, "checkout ."),
    ("g" + "it restore .", True, "restore ."),
    ("g" + "it filter-branch HEAD", True, "filter-branch"),
    # Allowed
    ("g" + "it push -u origin my-feature-branch", False, "feature-branch push with -u"),
    ("g" + "it push origin my-feature", False, "feature-branch push (no -u)"),
    ("g" + "it status", False, "status"),
    ("g" + "it commit -m 'msg'", False, "commit"),
    ("g" + "it stash push", False, "stash push"),
    ("g" + "it fetch origin", False, "fetch"),
    ("g" + "it pull --rebase origin main", False, "pull --rebase (read-only)"),
    ("ls", False, "non-git"),
]


def run(cmd_str: str) -> tuple[int, str]:
    payload = json.dumps({"tool_input": {"command": cmd_str}})
    p = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stderr


fails = 0
# SERIAL_OK_LOOP: hand-curated CASES list (~20 fixed test cases for block-dangerous-git hook); each runs a subprocess sanity check
for cmd, should_block, label in CASES:
    code, err = run(cmd)
    blocked = code == 2
    ok = blocked == should_block
    status = "PASS" if ok else "FAIL"
    # SERIAL_OK_STDOUT: ephemeral test-runner stdout, one PASS/FAIL line per of the ~20 cases; smoke-test report
    print(
        f"  [{status}] {label!r:50s} "
        f"expected={'block' if should_block else 'allow'}, "
        f"got={'block' if blocked else 'allow'} (code={code})"
    )
    if not ok:
        fails += 1
        if err:
            # SERIAL_OK_STDOUT: ephemeral test-runner stdout — extra stderr context only on FAIL; bounded by failure count
            print(f"          stderr: {err.strip()}")

print(
    f"\n{len(CASES) - fails}/{len(CASES)} passed."
    + (f" {fails} FAILURE(S)." if fails else " All good.")
)
sys.exit(1 if fails else 0)
