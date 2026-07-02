#!/usr/bin/env python3
# REASON: PreToolUse Bash hook — physically blocks dangerous git commands (force-push,
# hard reset, branch -D, filter-branch, reflog expire) at the system level so they
# can't be executed even if AI judgment slips, because these operations rewrite or
# destroy history that cannot be recovered without deliberate user action.
"""
.agent-kit/adapters/claude/hooks/block-dangerous-git.py

PreToolUse hook for Claude Code Bash tool. Reads the tool input as JSON
on stdin, extracts the command, and exits with code 2 if it matches a
dangerous pattern. Otherwise exits 0 silently and lets the command run.

Adapted from mattpocock/skills/git-guardrails-claude-code (originally
bash + jq) to Python because this scaffold targets machines that may
not have jq installed.

  Blocked:
    - git push --force / -f / --force-with-lease
    - git push --mirror / --delete
    - git reset --hard / --keep
    - git clean -f / -fd
    - git branch -D
    - git checkout . / git restore .
    - git filter-branch
    - git reflog expire --expire-unreachable

  Allowed (so normal feature-branch work isn't impeded):
    - git push (to any branch, no --force)
    - git push -u origin <branch>
    - git push origin HEAD

If you need to do a blocked operation, ask the user — don't try to
work around the hook.

Exit codes (per Claude Code hook protocol):
  0 — allow the command
  2 — block the command, message on stderr is shown to the model
"""

from __future__ import annotations

import json
import re
import sys


# Each entry: (regex, human-readable description).
# Patterns are intentionally narrow to avoid false positives.
#
# Normal `git push` to any branch (including master/main) is allowed.
# We block ONLY history-rewrite and mass-destructive ops, NOT
# branch-targeted normal pushes.
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    # Force pushes — any flavour. Rewrites upstream history.
    (r"\bgit\s+push\b.*\s--force(?:-with-lease)?\b", "git push --force / --force-with-lease"),
    (r"\bgit\s+push\b.*\s-f(?:\s|$)", "git push -f"),
    # Mirror / delete pushes are mass-destructive
    (r"\bgit\s+push\b.*\s--mirror\b", "git push --mirror"),
    (r"\bgit\s+push\b.*\s--delete\b", "git push --delete"),
    # Hard resets — discards uncommitted work
    (r"\bgit\s+reset\s+(?:--hard|--keep)\b", "git reset --hard"),
    # Working-tree wipes
    (r"\bgit\s+clean\s+[^|;&]*-[a-z]*f", "git clean -f"),
    (r"\bgit\s+checkout\s+\.(?:\s|$)", "git checkout ."),
    (r"\bgit\s+restore\s+\.(?:\s|$)", "git restore ."),
    # Branch deletes (capital-D forces deletion of unmerged work)
    (r"\bgit\s+branch\s+(?:-D|--delete\s+--force)\b", "git branch -D"),
    # Filter-branch / reflog expire — history rewrites
    (r"\bgit\s+filter-branch\b", "git filter-branch"),
    (r"\bgit\s+reflog\s+expire\b.*--expire-unreachable", "git reflog expire --expire-unreachable"),
]


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # If we can't parse, fail open — let Claude Code surface the error.
        return 0

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd.strip():
        return 0

    # SERIAL_OK_LOOP: walks DANGEROUS_PATTERNS (~11 entries); first-match-wins; per-Bash-call invocation, hot path is tiny
    for pattern, label in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd):
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — one BLOCKED message per invocation; ephemeral, fires on at-most one match
            print(
                f"BLOCKED: '{cmd}' matches dangerous pattern "
                f"'{label}'. The user has prevented you from doing this. "
                f"If you genuinely need this operation, ask the user "
                f"first — do NOT try to bypass the hook.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
