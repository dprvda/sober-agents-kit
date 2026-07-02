# REASON: SessionStart hook that force-injects the full project-knowledge corpus (latest handoff + continue-directive, CLAUDE.md, .agent-kit/adapters/claude/README.md, every docs/*.md, recent git log, open-issue titles) into a fresh session after /clear or /compact, because the SessionStart additionalContext field is hard-capped at 10000 chars per hook invocation so a single hook cannot deliver large corpora — this script is invoked once per chunk (--chunk N) across many registered hook entries, each emitting one <=9800-char slice instead of silently dropping content.
"""SessionStart context-injection hook (per-chunk).

The SessionStart ``additionalContext`` field is capped at 10000 chars
per hook invocation. To force-inject the whole project-knowledge corpus we
register N SessionStart hook entries, each calling this script with a
distinct ``--chunk`` index; the script slices the corpus into
<=9800-char, doc-boundary-aligned chunks and emits the requested one.

Corpus order: latest handoff (+ a continue-the-handoff directive),
CLAUDE.md, .agent-kit/adapters/claude/README.md, docs/*.md, an auto-generated ADR index,
the recent ~50 commit subjects, open-issue titles.

Output: one JSON object
``{"hookSpecificOutput": {"hookEventName": "SessionStart",
"additionalContext": "<chunk>"}}`` to stdout. ``--chunk`` beyond the
corpus emits an empty additionalContext (lets us register spare hook
slots so doc growth never silently drops content). ``--count`` prints
the current chunk count (used to size the settings.json hook list).
JSON is emitted with ensure_ascii so stdout stays pure ASCII — a
SessionStart hook on Windows must not crash on a cp1252 console.
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# 10000-char hard cap on additionalContext, minus per-chunk header room.
CHUNK = 9800


def _read(rel: str) -> str | None:
    """Repo-relative file read; None on any failure (never raises)."""
    try:
        return (REPO / rel).read_text(encoding="utf-8")
    except OSError:
        return None


def _latest_handoff() -> str | None:
    """Newest handoff (filename-sorted = chronological) + a directive
    telling the fresh session to continue that handoff's action list."""
    hs = sorted(glob.glob(str(REPO / ".claude/handoffs/handoff_*.md")))
    if not hs:
        return None
    try:
        body = Path(hs[-1]).read_text(encoding="utf-8")
    except OSError:
        return None
    directive = (
        "# ACTION FOR THIS SESSION\n\n"
        "Continue the work described in the latest session handoff "
        "below. Read its Action list in full and execute it top-down.\n\n"
        "---\n\n"
    )
    return directive + body


def _adr_index() -> str:
    """Auto-generated index of every ADR — first H1 line of each file."""
    rows = []
    for f in sorted(glob.glob(str(REPO / "docs/decisions/ADR-*.md"))):
        title = Path(f).stem
        try:
            for ln in Path(f).read_text(encoding="utf-8").splitlines():
                if ln.startswith("# "):
                    title = ln[2:].strip()
                    break
        except OSError:
            pass
        rows.append(f"- {title}")
    return "# ADR index (auto-generated)\n\n" + "\n".join(rows) + "\n"


def _recent_commits() -> str:
    """Last ~50 commit subjects via git log."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "log", "-50", "--pretty=format:%h %s"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = "(git log unavailable)"
    return "# Recent commits (last ~50)\n\n```\n" + out + "\n```\n"


def _open_issues() -> str:
    """Open GitHub issue titles from the auto-maintained .gh-issues.md
    (titles only — the ``### #NNN ...`` lines, not the bodies)."""
    body = _read(".gh-issues.md")
    if body is None:
        return "# Open GitHub issues\n\n(.gh-issues.md not found — optional file)\n"
    titles = [ln[4:].strip() for ln in body.splitlines() if ln.startswith("### #")]
    return "# Open GitHub issues — titles\n\n" + "\n".join(
        f"- {t}" for t in titles
    ) + "\n"


def _build_corpus() -> list[tuple[str, str]]:
    """Ordered (label, text) items — the full injected corpus.

    Generic order:
      1. Latest .claude/handoffs/handoff_*.md (newest) + continue-directive
      2. AGENTS.md (the canonical rules, every tool)
      3. .agent-kit/adapters/claude/README.md (if present)
      4. docs/*.md  (sorted alphabetically)
      5. ADR index  (auto-generated from docs/decisions/ADR-*.md)
      6. Recent git log (~50 commits)
      7. .gh-issues.md titles (if present)
    """
    items: list[tuple[str, str]] = []

    # 0. Live session progress (the continuity ledger — trumps recollection after a compaction)
    prog = _read(".claude/session-progress.md")
    if prog:
        items.append(("LIVE SESSION PROGRESS — trust this + git log over your own recollection", prog))

    # 1. Latest handoff + continue-directive
    handoff = _latest_handoff()
    if handoff:
        items.append(("latest handoff + continue-directive", handoff))

    # 2-3. Primary orientation docs
    for rel in ("AGENTS.md", ".agent-kit/adapters/claude/README.md"):
        text = _read(rel)
        if text:
            items.append((rel, text))

    # 4. All docs/*.md (cross-cutting topic docs, ADRs excluded here)
    for f in sorted(glob.glob(str(REPO / "docs/*.md"))):
        rel = "docs/" + Path(f).name
        text = _read(rel)
        if text:
            items.append((rel, text))

    # 5. ADR index (auto-generated)
    items.append(("ADR index", _adr_index()))

    # 6. Recent commits
    items.append(("recent commits", _recent_commits()))

    # 7. Open issues (optional — skipped gracefully if file absent)
    items.append(("open issues", _open_issues()))

    return items


def _chunks() -> list[tuple[str, str]]:
    """Doc-boundary-aligned <=CHUNK-char slices. A doc never shares a
    chunk with another doc; a doc larger than CHUNK spans several."""
    out: list[tuple[str, str]] = []
    for label, text in _build_corpus():
        pieces = [text[i:i + CHUNK] for i in range(0, len(text), CHUNK)] or [""]
        for idx, piece in enumerate(pieces):
            plabel = label if len(pieces) == 1 else f"{label} (part {idx + 1}/{len(pieces)})"
            out.append((plabel, piece))
    return out


def _emit(additional_context: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": additional_context,
    }}, ensure_ascii=True))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, help="1-based chunk index to emit")
    ap.add_argument("--count", action="store_true",
                    help="print the current chunk count and exit")
    ap.add_argument("--all", action="store_true",
                    help="print the whole corpus as plain text (no hook JSON) — the "
                         "tool-neutral path: any agent runs this once at session start "
                         "per the AGENTS.md first-action instruction")
    args = ap.parse_args()

    chunks = _chunks()
    if args.count:
        print(len(chunks))
        return 0
    if args.all:
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except AttributeError:
            pass
        for label, text in chunks:
            print(f"\n===== [{label}] =====\n")
            print(text)
        return 0
    if args.chunk is None:
        print("error: --chunk, --count or --all required", file=sys.stderr)
        return 2
    if args.chunk < 1 or args.chunk > len(chunks):
        # Beyond the corpus — spare hook slot, inject nothing.
        _emit("")
        return 0

    label, text = chunks[args.chunk - 1]
    header = (
        f"[__PROJECT_NAME__ auto-injected context — chunk {args.chunk}/{len(chunks)}"
        f" — {label}]\n\n"
    )
    _emit(header + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
