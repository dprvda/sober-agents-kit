#!/usr/bin/env python3
# REASON: PreToolUse Bash hook — fires only on `git commit`, re-prints critical sections
# of CLAUDE.md (global + project) to stderr so the rules land back in Claude's context
# just before the commit, because long autonomous sessions drift from CLAUDE.md rules
# even when those rules were loaded at session start. Complements block-dangerous-git
# (physical blocks).
"""
.claude/dprvda-kit/hooks/remind-claude-md.py

PreToolUse hook for Claude Code Bash tool. Fires ONLY on `git commit`
commands. Reads CLAUDE.md and prints the critical-rules sections to
stderr — Claude Code sees stderr from a passing hook (exit 0) as
part of the tool result, so the rules land back in context just
before the commit happens.

Why
---
Long autonomous sessions drift from CLAUDE.md rules even when those
rules are loaded at session start. The classic failure mode: AI
skips hook verification, force-pushes, amends published commits,
fabricates "done" status, or commits without updating relevant docs.
Re-injecting the rules at commit time makes that drift much harder.

What gets printed
-----------------
- A header pointing at CLAUDE.md (so the AI knows where to read more)
- Critical sections from the GLOBAL ~/.claude/CLAUDE.md:
    Defaults to all "## " headers, with well-known discipline headings
    pre-listed in GLOBAL_SECTIONS. Extend as needed for your project.
- Key sections from the PROJECT ./CLAUDE.md:
    Listed in PROJECT_SECTIONS. These are generic examples — replace
    with the actual "## " headers that exist in your project's CLAUDE.md.

NOT the full file — that would be too large on every commit. Just the
sections that matter at commit time.

Exit codes (per Claude Code hook protocol)
-------------------------------------------
  0 — allow the command (always — this hook never blocks)
  2 — only on internal failure (e.g. CLAUDE.md missing)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# Match git commit commands. Allow flags (-m, --amend, --no-edit, etc.)
# but NOT git status / git log / etc.
COMMIT_PATTERN = re.compile(r"\bgit\s+commit\b")

# Sections to extract from the GLOBAL CLAUDE.md (~/.claude/CLAUDE.md) —
# the universal discipline rules that apply to every project.
# These are the well-known headings; the hook also falls back to printing
# the full file if none match (so renamed headers never cause a silent gap).
GLOBAL_SECTIONS = [
    "## IMPORTANT: Honesty",
    "## IMPORTANT: Verify your work",
    "## Root causes, not workarounds",
    "## Process management",
    "## Communication",
    "## IMPORTANT: Documentation discipline",
    # Add or rename entries here to match your global CLAUDE.md headings.
]

# Sections to extract from the PROJECT CLAUDE.md (./CLAUDE.md).
# These are EXAMPLES — replace with the actual "## " headers that exist
# in your project's CLAUDE.md. The fallback prints the full file if none match.
PROJECT_SECTIONS = [
    "## Coding Rules",
    "## Pre-approved autonomous operations",
    "## Documentation drift control",
    # Add or rename entries here to match your project CLAUDE.md headings.
]


def repo_root() -> Path:
    """Return repo root via $CLAUDE_PROJECT_DIR or cwd fallback."""
    import os
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        p = Path(env)
        if p.exists():
            return p
    return Path.cwd()


def extract_sections(claude_md: str, headers: list[str]) -> list[tuple[str, str]]:
    """Return [(header, body), ...] for each requested section, in
    file-order. Body runs from the header line (inclusive) to the
    next `^## ` header (exclusive)."""
    out: list[tuple[str, str]] = []
    lines = claude_md.splitlines()
    i = 0
    # SERIAL_OK_LOOP: walks CLAUDE.md lines (~80-200 lines) once to extract sections; index-based, can't vectorise (next-section detection is stateful)
    while i < len(lines):
        line = lines[i]
        if line.strip() in headers:
            header = line.strip()
            j = i + 1
            # SERIAL_OK_LOOP: inner walk to find next `## ` boundary; bounded by section length (<=30 lines), inherently sequential
            while j < len(lines) and not lines[j].startswith("## "):
                j += 1
            body = "\n".join(lines[i:j]).rstrip()
            out.append((header, body))
            i = j
        else:
            i += 1
    return out


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd.strip():
        return 0

    if not COMMIT_PATTERN.search(cmd):
        return 0

    project_path = repo_root() / "AGENTS.md"          # canonical rules (CLAUDE.md is just the bridge)
    if not project_path.exists():
        project_path = repo_root() / "CLAUDE.md"      # pre-flip installs
    global_path = Path.home() / ".claude" / "CLAUDE.md"

    print(
        "─── CLAUDE.md reminder (refreshed before this commit) ───",
        file=sys.stderr,
    )

    # SERIAL_OK_LOOP: 2-element fixed tuple (GLOBAL, PROJECT) — refreshes both CLAUDE.md files into stderr before commit
    for label, path, headers in (
        ("GLOBAL", global_path, GLOBAL_SECTIONS),
        ("PROJECT", project_path, PROJECT_SECTIONS),
    ):
        if not path.exists():
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — one-shot warning when CLAUDE.md missing; ephemeral pre-commit notification
            print(
                f"\n[{label}] WARNING: not found at {path} — skipped.",
                file=sys.stderr,
            )
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — one-shot warning on read failure; ephemeral pre-commit notification
            print(f"\n[{label}] WARNING: cannot read: {e}", file=sys.stderr)
            continue

        sections = extract_sections(text, headers)
        if not sections:
            # Headers may have been renamed — surface the whole file as
            # fallback so context is still refreshed.
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — fallback warning when section headers don't match; ephemeral pre-commit notification
            print(
                f"\n[{label}] (Headers from "
                f"{'GLOBAL' if label == 'GLOBAL' else 'PROJECT'}_SECTIONS not "
                "found — printing full file as fallback. Update the list in "
                ".claude/dprvda-kit/hooks/remind-claude-md.py if header names changed.)\n",
                file=sys.stderr,
            )
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — full-file fallback dump (rare, only if section headers diverge); ephemeral
            print(text, file=sys.stderr)
            continue

        # SERIAL_OK_STDOUT: PreToolUse hook stderr — section header banner; ephemeral pre-commit refresh
        print(
            f"\n=== {label} CLAUDE.md ({path}) ===\n",
            file=sys.stderr,
        )
        # SERIAL_OK_LOOP: extracted sections from CLAUDE.md (~3-7 sections per file); CLI stderr render
        for header, body in sections:
            # SERIAL_OK_STDOUT: PreToolUse hook stderr — one section body per loop iter; ephemeral pre-commit refresh
            print(f"\n{body}\n", file=sys.stderr)

    print(
        "\n─── End of CLAUDE.md reminder ───\n"
        "Now proceed with the commit. NEVER use --no-verify. "
        "Force-push to main/master ALWAYS requires explicit user approval. "
        "Verify the commit landed and any CI gates pass afterward.\n",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
