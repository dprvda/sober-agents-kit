#!/usr/bin/env python3
# REASON: PreToolUse Bash hook — when the bash command is about to launch a script
# (python <file>.py / bash <file>.sh / ./<file>.{py,sh,bash}), it spawns the AI judge
# .agent-kit/gates/critic_llm.py --files <target> --no-mutate to get a verdict on that
# script before it runs, and blocks the launch only on severity=block. The judge
# prepends an LLM_REVIEW_BLOCK comment into the source file on warn/block (a
# truncation-safe persistent record that survives stderr truncation, context clears,
# and scrollback caps); the hook also surfaces the sidecar JSON path in its BLOCKED
# banner so the AI has a second persistent fallback. It soft-passes on judge
# unavailable / timeout / internal error because an offline session still needs to
# run scripts, instead of hard-blocking every launch when the API is down.
"""
.agent-kit/adapters/claude/hooks/check-script-launch.py

PreToolUse hook for Claude Code Bash tool. When the command is about to
launch a script, fan it through the AI judge `.agent-kit/gates/critic_llm.py`
in working-tree mode. Block only when the judge returns severity=block.

Detection (file extracted from command via regex):
  - `python <path>.py`              → review <path>.py
  - `python -m <module>`            → skipped (module syntax, no path)
  - `bash <path>.sh`                → review <path>.sh
  - `sh <path>.sh`                  → review <path>.sh
  - `./<path>.{py,sh,bash}`         → review <path>
  - Other commands                  → no match, allow

Truncation-safety mechanisms (three layers, in order of robustness):
  1. LLM_REVIEW_BLOCK comment prepended to the source file on warn/block —
     bytes on disk, the AI sees it on the next `Read`, survives any
     stderr/context truncation. The judge automatically strips the
     block on the next ok verdict (after the issues are fixed).
  2. Sidecar JSON at .llm-review/<encoded-path>.json — full
     verdict (severity, summary, issues[], sha256), persisted on every
     review. The hook prints this path in the BLOCKED banner so the AI
     can `Read` it directly if hook stderr is truncated.
  3. Hook stderr (BLOCKED banner + relayed critic_llm stderr) —
     the transient surface; head/tail truncation can lose the body, so
     layers 1 + 2 are the load-bearing records.

Verdict mapping (rc from critic_llm):
  - rc=0 (ok / warn / judge soft-pass) → allow
  - rc=1 (block)                       → BLOCK, relay stderr to AI session
  - rc=2 (internal error)              → allow (fail-open)
  - subprocess timeout / spawn fail    → allow (fail-open)

Judge unavailable (no API key, network down, transient API errors) falls
into rc=0 inside critic_llm itself — the AI judge is best-effort, not a
hard gate, so an offline session still runs scripts.

Exit codes (per Claude Code hook protocol):
  0 — allow (no script detected, or judge said ok/warn/unavailable)
  2 — block, message on stderr is shown to the model
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
GATE = REPO_ROOT / ".claude" / "agent-kit" / "gates" / "critic_llm.py"
SIDECAR_DIR = REPO_ROOT / ".llm-review"

# Hard wall on the AI call. Cold judge calls typically land in 5-15 s; the
# first call after a tree-wide reset can be slower. 22 s leaves ~3 s slack
# under the harness's 25 s hook timeout in .claude/settings.json.
GATE_TIMEOUT_S = 22


def sidecar_path_for(target: Path) -> Path:
    """Mirror .agent-kit/gates/critic_llm.py::sidecar_path_for so the hook
    can name the persistent verdict record without parsing JSON output."""
    rel = target.relative_to(REPO_ROOT) if target.is_absolute() else target
    safe = rel.as_posix().replace("/", "__")
    return SIDECAR_DIR / f"{safe}.json"

# Patterns that extract a script path from a Bash command. Each pattern
# captures the path. Order matters — first match wins per command.
SCRIPT_LAUNCH_PATTERNS = [
    # `python foo.py` (with optional flags before the path), but NOT `python -m`
    re.compile(r"\bpython3?\b(?!\s+-m\b)(?:\s+-[A-Za-z]+)*\s+([^\s|;&<>]+\.py)\b"),
    # `bash foo.sh` / `sh foo.sh`
    re.compile(r"\b(?:bash|sh)\b\s+([^\s|;&<>]+\.(?:sh|bash))\b"),
    # `./foo.py` / `./foo.sh` (entry-point style)
    re.compile(r"(?:^|\s)(\./[^\s|;&<>]+\.(?:py|sh|bash))\b"),
]


def main() -> int:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return 0  # fail open — let Claude Code surface the parse error

    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not isinstance(cmd, str) or not cmd.strip():
        return 0

    # Extract every script path the command launches. A single command
    # might launch multiple files via `&&`; check each one.
    paths: list[str] = []
    for pat in SCRIPT_LAUNCH_PATTERNS:
        for m in pat.finditer(cmd):
            paths.append(m.group(1))
    if not paths:
        return 0

    # Resolve to absolute repo paths and dedupe while preserving order.
    seen: set[str] = set()
    targets: list[Path] = []
    for raw_path in paths:
        p = Path(raw_path)
        if not p.is_absolute():
            p = (REPO_ROOT / raw_path).resolve()
        else:
            p = p.resolve()
        if str(p) in seen:
            continue
        seen.add(str(p))
        if p.exists() and p.suffix in {".py", ".sh", ".bash"}:
            targets.append(p)
    if not targets:
        return 0

    if not GATE.exists():
        # AI judge missing — fail-open silently rather than blocking real work.
        return 0

    # One subprocess for the whole target set; critic_llm handles
    # parallelism internally and the sidecar cache makes repeat launches
    # of the same file near-instant. We pass --no-mutate at launch time so
    # the hook reviews the working tree without rewriting files mid-launch;
    # the judge still persists the verdict to the sidecar JSON, and on a
    # block it also prepends the in-source LLM_REVIEW_BLOCK as the most
    # truncation-safe signal (bytes on disk, AI sees it on next Read).
    cmd_args = [
        sys.executable,
        str(GATE),
        "--files",
        *[str(t) for t in targets],
        "--no-mutate",
    ]
    try:
        proc = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            timeout=GATE_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        # Don't stall bash launches on a slow / hung API call.
        return 0
    except (OSError, subprocess.SubprocessError):
        return 0

    if proc.returncode == 0 or proc.returncode == 2:
        # ok / warn / judge-unavailable / internal error → allow.
        return 0

    # rc == 1: at least one block verdict. Relay the gate's stderr to
    # the AI session and exit 2 to block the launch.
    target_rels = [t.relative_to(REPO_ROOT).as_posix() for t in targets]
    print(
        f"BLOCKED: AI judge returned severity=block on "
        f"{', '.join(target_rels)}.\n",
        file=sys.stderr,
    )
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    # Three-layer truncation-safety: the in-source LLM_REVIEW_BLOCK is layer
    # 1 (bytes on disk, survives any stderr truncation); the sidecar JSON is
    # layer 2 (also persistent — full verdict including issues[] + sha256);
    # the stderr above is layer 3 (transient). Surface the layer-1 + layer-2
    # paths explicitly so the AI session can recover even if this stderr
    # gets head/tail-truncated in the tool result.
    print("\nPersistent records (truncation-safe):", file=sys.stderr)
    for t, rel in zip(targets, target_rels):
        sc = sidecar_path_for(t).relative_to(REPO_ROOT).as_posix()
        print(
            f"  - in-source LLM_REVIEW_BLOCK at top of {rel} (just prepended)\n"
            f"  - sidecar JSON: {sc} (full verdict: severity, summary, issues[], sha256)",
            file=sys.stderr,
        )
    print(
        "\nFix path:\n"
        "  1. Read the LLM_REVIEW_BLOCK at the top of each blocked file (or the\n"
        "     sidecar JSON if stderr is truncated).\n"
        "  2. Address each line-numbered item — the line numbers point into\n"
        "     the file BELOW the block.\n"
        "  3. Remove the entire LLM_REVIEW_BLOCK (top marker through end marker).\n"
        "  4. Re-issue the command — the sidecar cache will re-review on the\n"
        "     new sha256 and pass once the issues are gone (the judge also\n"
        "     auto-strips the block on the next ok verdict).\n"
        "\nGate: .agent-kit/gates/critic_llm.py.\n"
        "Hook: .agent-kit/adapters/claude/hooks/check-script-launch.py.\n",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
