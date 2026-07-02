#!/usr/bin/env python3
# REASON: PostToolUse Bash hook -- emits a short JSON additionalContext nudge to the model after a `gh issue|pr|search|api|release|workflow|run` invocation, because the model should re-route the NEXT lookup to mcp__github__* (typed structured JSON, batches via HTTP/2 with PAT auth, one round-trip vs N gh subprocess spawns). PostToolUse + additionalContext is the only non-blocking shape the harness surfaces to the model -- plain PreToolUse stderr is silently dropped. The nudge is one line naming the exact MCP method-multiplexed tool so the model doesn't guess get_issue (which does NOT exist; it's issue_read with method='get').
"""
.agent-kit/adapters/claude/hooks/nudge-to-github-mcp.py

PostToolUse hook for Claude Code Bash tool. Detects `gh` CLI usage that
the GitHub MCP server (mcp__github__*) can handle more efficiently,
and emits a JSON additionalContext nudge with the equivalent MCP call.
Never blocks.

Important shape note (do NOT guess this — read the nudge it emits)
------------------------------------------------------------------
The official github/github-mcp-server uses **method-multiplexed**
tools, NOT one tool per operation. There is NO standalone
``mcp__github__get_issue``; it's ``mcp__github__issue_read`` with
``method='get'``. Same for ``pull_request_read``. A model writing
``mcp__github__get_issue`` will fail with InputValidationError.

When the nudge fires
--------------------
Command matches ``\\bgh\\s+(issue|pr|api|release|run|search|workflow|repo)\\b``
AND the operation looks like a read (view/list/search/diff/comments).

When the nudge stays silent
---------------------------
  - ``gh auth status`` / ``gh --version`` / ``gh config ...`` — admin
    ops the MCP doesn't cover anyway.
  - The bash command is inside a here-doc or a quoted string that
    happens to mention ``gh`` (we check the first word, not substrings
    anywhere).
  - Command is being executed from inside ``scripts/`` (those are
    committed scripts with a reason to use ``gh`` directly).
  - JSON cannot be parsed (fail-open).

Exit codes
----------
  0 — always (nudge never blocks)
"""

from __future__ import annotations

import json
import re
import sys


GH_INVOCATION_RE = re.compile(r"\bgh\s+(issue|pr|api|release|run|search|workflow|repo)\b")

# Admin/config commands the MCP doesn't cover. Stay silent on these.
GH_ADMIN_RE = re.compile(r"\bgh\s+(auth|config|alias|completion|extension|--version|--help)\b")

# Map of (subcommand, action) -> MCP-equivalent hint. Action is the
# second word after `gh issue` / `gh pr`. The hint is intentionally
# brief — full tool schemas live in docs/mcp-stack.md.
HINTS: dict[tuple[str, str], str] = {
    ("issue", "view"): "mcp__github__issue_read(method='get', owner=..., repo=..., issue_number=N)",
    ("issue", "list"): "mcp__github__list_issues(owner=..., repo=..., state='open')",
    ("issue", "search"): "mcp__github__search_issues(query='...')",
    ("issue", "comments"): "mcp__github__issue_read(method='get_comments', owner=..., repo=..., issue_number=N)",
    ("pr", "view"): "mcp__github__pull_request_read(method='get', owner=..., repo=..., pullNumber=N)",
    ("pr", "diff"): "mcp__github__pull_request_read(method='get_diff', owner=..., repo=..., pullNumber=N)",
    ("pr", "comments"): "mcp__github__pull_request_read(method='get_comments', owner=..., repo=..., pullNumber=N)",
    ("pr", "list"): "mcp__github__list_pull_requests(owner=..., repo=..., state='open')",
    ("pr", "search"): "mcp__github__search_pull_requests(query='...')",
    ("pr", "checks"): "mcp__github__pull_request_read(method='get_check_runs', owner=..., repo=..., pullNumber=N)",
    ("search", "issues"): "mcp__github__search_issues(query='...')",
    ("search", "prs"): "mcp__github__search_pull_requests(query='...')",
    ("search", "code"): "mcp__github__search_code(query='...')",
    ("search", "commits"): "mcp__github__search_commits(query='...')",
    ("search", "repos"): "mcp__github__search_repositories(query='...')",
    ("api", ""): "mcp__github__<resource>_read / search_<resource> — pick the typed tool over generic gh api",
    ("release", "list"): "mcp__github__list_releases(owner=..., repo=...)",
    ("release", "view"): "mcp__github__get_release_by_tag(owner=..., repo=..., tag=...)",
    ("repo", "view"): "mcp__github__get_file_contents / get_repository_tree (no get_repo tool)",
}


def parse_first_words(cmd: str) -> tuple[str | None, str | None]:
    """Return (subcommand, action) — e.g. ('issue', 'view') for
    ``gh issue view 644``. Returns (None, None) if cmd doesn't start
    with ``gh `` (anchored to defeat heredoc / substring false-fires)."""
    stripped = cmd.lstrip()
    if not stripped.startswith("gh "):
        # Note: command starting with leading whitespace is fine — but
        # the FIRST non-whitespace word must be `gh`. This avoids
        # nudging on `cat << EOF; gh issue ...` and similar.
        return None, None
    parts = stripped.split(None, 3)
    if len(parts) < 2:
        return None, None
    sub = parts[1]
    action = parts[2] if len(parts) >= 3 else ""
    return sub, action


def build_nudge(sub: str, action: str) -> str:
    hint = HINTS.get((sub, action))
    if hint is None:
        hint = f"mcp__github__* (see docs/mcp-stack.md); method-multiplex (issue_read method=get, NOT get_issue)"
    return f"NUDGE: 'gh {sub} {action}' -- try {hint}."


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0  # fail-open

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd.strip():
        return 0

    if GH_ADMIN_RE.search(cmd):
        return 0  # admin/config — MCP doesn't cover, stay silent
    if not GH_INVOCATION_RE.search(cmd):
        return 0

    sub, action = parse_first_words(cmd)
    if sub is None:
        # `gh` appeared mid-command (heredoc / pipe target / substring)
        # — don't nudge on that.
        return 0

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": build_nudge(sub, action or ""),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
