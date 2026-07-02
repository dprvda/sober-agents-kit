#!/usr/bin/env python3
# REASON: PostToolUse Grep hook -- emits a short JSON additionalContext nudge to the model after a Grep whose pattern looks like a code identifier in a code dir, because the model should re-route the NEXT lookup to mcp__serena__find_symbol (which returns body + location in one call). PostToolUse + additionalContext is the only non-blocking shape the harness surfaces to the model -- plain PreToolUse stderr is silently dropped. The nudge is one line + one MCP call hint -- short on purpose so the per-call context cost stays under ~120 chars. No existing hook covers this PostToolUse channel -- the prior PreToolUse stderr emission was invisible to the model and only documented the routing rule.
"""
.claude/dprvda-kit/hooks/nudge-to-serena.py

PostToolUse hook for Claude Code Grep tool. Reads tool input JSON on
stdin, inspects the `pattern` (and `path`) field, and emits a JSON
additionalContext nudge pointing at Serena MCP when the pattern looks
like a code identifier the model is hunting symbol info for.

Exit codes (per Claude Code hook protocol):
  0 — always (this hook never blocks; nudge is informational only)
  2 — never used (would block the grep, which is not the goal)

When the nudge fires
--------------------
ALL must hold:
  - Pattern matches ``^[A-Za-z_][A-Za-z0-9_]*$`` (identifier-shape — no
    regex metachars, no whitespace, no quoting).
  - Pattern length >= MIN_IDENTIFIER_LEN (4) — shorter is too generic
    (``mod`` / ``use`` / ``fn``).
  - Pattern is NOT in IDENTIFIER_STOPLIST (TODO / FIXME / XXX / HACK
    are real text searches, not symbol queries).
  - Either no path is set OR path falls under a known code directory
    (see CODE_DIR_PREFIXES below — edit this list to match your project
    layout). A grep over ``docs/`` or ``runs/`` stays silent.

When the nudge stays silent
---------------------------
  - Pattern contains regex metachars (``.``, ``*``, ``+``, ``[``, ``\\``,
    ``|``, ``?``, ``(``, ``)``, ``{``, ``}``, ``^``, ``$``).
  - Pattern is shorter than 4 chars.
  - Pattern is a known text token (TODO/FIXME/…).
  - Path is set and falls outside code dirs.
  - ``multiline: true`` (cross-line text search, not a symbol lookup).
  - JSON cannot be parsed (fail-open).

Why a soft nudge instead of a hard block
----------------------------------------
Serena's responses can be very large on broad symbol queries
(``find_referencing_symbols`` of a hot type returns every caller with
surrounding context — 10k+ tokens). Grep IS the right tool for genuine
text searches. We steer the model toward Serena where it wins
(targeted symbol lookups) without amputating the cases where grep is
right. After 2-3 sessions the model defaults to Serena for symbol-y
queries on its own; this hook is the training signal.
"""

from __future__ import annotations

import json
import re
import sys

MIN_IDENTIFIER_LEN = 4

# Identifiers under this length are too generic to be useful symbol
# queries (mod/use/fn/let/pub/...). Let grep handle them.

IDENTIFIER_STOPLIST = frozenset(
    {
        "TODO",
        "FIXME",
        "XXX",
        "HACK",
        "NOTE",
        "BUG",
        "WARN",
        "ERROR",
        # Rust + Python keywords that look identifier-shaped
        "self",
        "impl",
        "trait",
        "struct",
        "enum",
        "match",
        "where",
        "async",
        "await",
        "yield",
        "class",
        "import",
        "return",
        "raise",
        "lambda",
        "global",
        "nonlocal",
    }
)

IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Pattern is regex-shaped if it contains any of these metachars. We
# build the set verbatim so a reader can audit it; a literal class
# would be denser but harder to scan.
REGEX_METACHARS = frozenset(".*+[\\|?(){}^$")

# Roots inside the project where source code lives. A grep into one of
# these (or no explicit path = full-repo grep) earns the nudge.
# EDIT THIS LIST to match your project's directory layout.
CODE_DIR_PREFIXES = (
    "src/",
    "lib/",
    "app/",
    "scripts/",
    "packages/",
)


def is_identifier(pattern: str) -> bool:
    if len(pattern) < MIN_IDENTIFIER_LEN:
        return False
    if pattern in IDENTIFIER_STOPLIST:
        return False
    if any(ch in REGEX_METACHARS for ch in pattern):
        return False
    return bool(IDENTIFIER_RE.match(pattern))


def is_code_path(path: str | None) -> bool:
    if not path:
        # No path = whole-repo grep. Treat as code-relevant — the model
        # is probably hunting a symbol across the workspace.
        return True
    # Normalize Windows backslashes for prefix matching.
    norm = path.replace("\\", "/").lstrip("./")
    return any(norm.startswith(prefix) for prefix in CODE_DIR_PREFIXES)


def build_nudge(pattern: str) -> str:
    return (
        f"NUDGE: '{pattern}' looks like a symbol -- try "
        f"mcp__serena__find_symbol(name_path_pattern='{pattern}', "
        f"include_body=true). Rust impl methods: 'impl Struct/method'."
    )


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0  # fail-open

    tool_input = data.get("tool_input") or {}
    pattern = tool_input.get("pattern")
    path = tool_input.get("path")
    multiline = bool(tool_input.get("multiline"))

    if not isinstance(pattern, str) or not pattern.strip():
        return 0
    if multiline:
        # Cross-line text searches are never symbol queries.
        return 0
    if not is_identifier(pattern):
        return 0
    if not is_code_path(path):
        return 0

    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": build_nudge(pattern),
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
