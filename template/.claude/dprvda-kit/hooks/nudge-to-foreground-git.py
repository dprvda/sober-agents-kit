#!/usr/bin/env python3
# REASON: PostToolUse Bash hook — emits a JSON additionalContext nudge after a backgrounded
# `git commit` (or `git push` / `pre-commit run`) reminding the model NOT to single-poll
# the resulting task with TaskOutput(block=true, timeout>120000), because git commits
# typically complete in 15-30s and long single-poll timeouts make the conversation appear
# hung for the full timeout window even after the commit lands.
"""
.claude/dprvda-kit/hooks/nudge-to-foreground-git.py

PostToolUse hook for Claude Code Bash tool. Reads tool input JSON on
stdin, inspects whether the command was a backgrounded git commit (or
git push / pre-commit run), and emits a JSON additionalContext nudge
steering the model toward either the foreground commit pattern OR a
multi-short-poll pattern instead of TaskOutput(block=true,
timeout>120000).

Background: A session pattern burned perceived "commit hangs" that were
actually polling artifacts — git commits completed in 15-30s but the
assistant was waiting on TaskOutput(timeout=600000).

Exit codes (per Claude Code hook protocol):
  0 — always (this hook never blocks; nudge is informational only)

When the nudge fires
--------------------
ALL must hold:
  - tool_input.run_in_background is True
  - tool_input.command contains 'git commit' OR 'git push' OR
    'pre-commit run' (case-sensitive — these tokens are typed verbatim
    in normal git workflows)

When the nudge stays silent
---------------------------
  - tool_input.run_in_background is False or absent (foreground —
    no polling issue)
  - command is not a git-write operation (legitimate long-running
    backgrounds like build / test / long-running tasks get no nudge —
    those genuinely need to wait, and the multi-poll pattern applies
    but is less universally beneficial than for git)
  - JSON unparseable (fail-open silently)

Why a soft nudge instead of a hard block
----------------------------------------
There are legitimate cases for backgrounded git commits (e.g.
intentionally proceeding with other work while the commit's hooks
run). The blocking antipattern is NOT 'background a git commit' — it's
'background a git commit AND THEN single-poll with timeout >120000'.
The model can't perfectly know the timeout it WILL pick until it
writes the next TaskOutput call, so this nudge fires at the earliest
moment (post-background) to plant the foreground-pattern reminder.

Better pattern recommended in the nudge:
  SECONDS=0 && git commit -F /tmp/msg.txt > /tmp/c.log 2>&1; \\
    echo "RC=$? TIME=${SECONDS}s"; git log --oneline -1
This foregrounds the commit, captures full output, reports timing.
~20s total turnaround, no polling needed.

If genuinely backgrounded: poll with TaskOutput(block=true,
timeout=30000) and re-poll if still running (multiple short polls
keep the conversation responsive; one long poll feels broken). Or
trust the auto-completion task-notification — the harness fires one
on completion.
"""

from __future__ import annotations

import json
import sys


GIT_WRITE_TOKENS = ("git commit", "git push", "pre-commit run")


def build_nudge() -> str:
    return (
        "NUDGE: backgrounded git command detected. Don't single-poll the "
        "resulting task with `TaskOutput(block=true, timeout=600000)` "
        "(or any timeout > 120000) — `git commit` completes in 15-30s "
        "but a long poll makes the conversation appear hung. "
        "Prefer: `SECONDS=0 && git commit -F /tmp/msg.txt > /tmp/c.log "
        "2>&1; echo \"RC=$? TIME=${SECONDS}s\"; git log --oneline -1` "
        "(foreground, ~20s, captures output). If you must background, "
        "poll with `TaskOutput(timeout=30000)` and re-poll, or trust "
        "the auto-completion notification."
    )


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        return 0  # fail-open

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    if not tool_input.get("run_in_background"):
        return 0

    command = tool_input.get("command") or ""
    if not isinstance(command, str):
        return 0

    if not any(token in command for token in GIT_WRITE_TOKENS):
        return 0

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": build_nudge(),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
