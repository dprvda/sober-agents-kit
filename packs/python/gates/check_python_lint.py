#!/usr/bin/env python3
# REASON: Lightweight Python lint gate — exists because ruff catches import errors, undefined names, and style violations that accumulate silently in large codebases, instead of waiting for CI to surface them after a push. Shells `ruff check --quiet` on staged .py files when ruff is installed; unavailable_pass (rc=0) when ruff is absent so a fresh checkout without ruff never blocks commits. Blocks only on ruff failures, not on warnings.
"""
check_python_lint — pre-commit ruff lint gate for staged Python files.

Accepts a list of .py file paths as arguments (pre-commit passes staged
filenames). When no arguments are given, checks the entire working tree.
When `ruff` is not installed, emits a one-line stderr notice and exits 0
(unavailable_pass policy — never break-by-default on a fresh checkout).

Exit codes:
- 0 — no lint errors OR ruff not installed
- 1 — ruff reported at least one error
- 2 — internal error (subprocess setup failed)

Usage (direct):
    python scripts/hooks/check_python_lint.py [file ...]

Usage (pre-commit):
    - id: check-python-lint
      name: Python ruff lint
      language: python
      entry: python scripts/hooks/check_python_lint.py
      types: [python]
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    if not shutil.which("ruff"):
        print(
            "[check_python_lint] ruff not installed — skipping (rc=0, "
            "unavailable_pass policy). Install via `pip install ruff`.",
            file=sys.stderr,
        )
        return 0

    # sys.argv[1:] are the staged file paths passed by pre-commit.
    # Fall back to `.` (whole tree) when invoked directly.
    targets: list[str] = sys.argv[1:] if len(sys.argv) > 1 else ["."]

    try:
        result = subprocess.run(
            ["ruff", "check", "--quiet", *targets],
            capture_output=False,  # let ruff write directly to stdout/stderr
            cwd=ROOT,
            check=False,
        )
    except OSError as exc:
        print(
            f"[check_python_lint] ERROR: failed to launch ruff: {exc}",
            file=sys.stderr,
        )
        return 2

    if result.returncode == 0:
        # Silent pass — matches the other gates' "all clean = no output" policy.
        return 0

    # ruff already printed its findings to stdout; just add a fix hint.
    print(
        "\n[check_python_lint] BLOCK — ruff reported errors above. "
        "Run `ruff check --fix` to auto-fix, or address manually.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
