#!/usr/bin/env python3
# REASON: existence-reason gate — forces every script file (py/rs/sh/bash) to declare WHY it exists at the top via `# REASON:` instead of silently creating duplicate scripts; no similar gate existed in the generic scaffold before this.
"""
scripts/check_file_reason.py — CI gate for the existence-reason marker.

Every script file in this repo (Python, Rust, shell, bash) must declare
WHY it exists in a `# REASON:` (Python/shell) or `// REASON:` (Rust)
comment at the top of the file. The reason text must be >= 30 chars and
should explain the file's role in a way that prevents the next AI
session from creating a duplicate. Good reasons:

  - "vs scripts/check_doc_freshness.py: this gate validates per-script
    intent, that one validates folder-README freshness"
  - "to enable bidirectional sync between two storage backends;
    no existing tool covers this"
  - "because pre-commit hooks run synchronously and we need an
    out-of-band runner for slow checks"

Bad reasons (will fail the heuristic):

  - "helper script" (too generic, < 30 chars after stripping)
  - "TODO" (no justification)
  - "see code" (defers without explaining)

Exit codes:
  0 — every script has a valid REASON marker (or is exempt)
  1 — at least one script is missing or has a too-short reason
  2 — internal error

Usage:
  python scripts/check_file_reason.py              # whole-repo scan
  python scripts/check_file_reason.py FILE...      # scan listed files only
  python scripts/check_file_reason.py --json       # machine-readable
  python scripts/check_file_reason.py --include-tests
                                                    # also scan tests/
Sibling .md: scripts/check_file_reason.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]

# Configurable: add or remove extensions to match the languages your project uses.
SCRIPT_EXTS = {".py", ".rs", ".sh", ".bash"}

# Directories never scanned in whole-repo mode.
EXEMPT_DIR_PARTS = {
    ".git", ".github", ".cache", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "target", "venv", ".venv", "env", "node_modules",
    "__pycache__", "dist", "build", "data", "runs", "logs",
    ".idea", "archive",
    # agent-worktree dirs (`.claude/worktrees/agent-*`) are transient git
    # worktrees created by parallel sub-agents. Their files are linked from
    # the same .git objects but live in subpaths of the main checkout — the
    # hook would otherwise re-scan every agent's full source tree on every
    # commit. The agent's own commit ran the gate inside the worktree so
    # coverage is preserved.
    "worktrees",
}
EXEMPT_TOP_PREFIXES = ("backup_",)
TEST_DIR_PREFIXES = ("tests/", "tests\\")

# Files exempt from the REASON requirement (boilerplate / language-mandated stubs).
EXEMPT_FILE_NAMES = {
    "__init__.py",
    "conftest.py",
    "setup.py",
    "build.rs",
    "_dummy.rs",
    # mod.rs is a re-export hub for a folder; the folder's purpose is
    # documented at the folder-README level. lib.rs / main.rs are NOT
    # exempt — a crate may produce both, and each needs its own purpose
    # statement above what the folder README says.
    "mod.rs",
}

# Marker syntax — top-of-file comment line.
# Python / shell: `# REASON: ...`
# Rust:           `// REASON: ...`
# Optional shebang line is allowed before the marker.
PY_SH_MARKER_RE = re.compile(r"^\s*#\s*REASON\s*:\s*(?P<reason>.+?)\s*$")
RS_MARKER_RE = re.compile(r"^\s*//\s*REASON\s*:\s*(?P<reason>.+?)\s*$")
SHEBANG_RE = re.compile(r"^#!\s*/")

MIN_REASON_CHARS = 30

# Heuristic for "substantive justification": at least one of these
# tokens should appear in the reason. Otherwise the marker is a generic
# rubber-stamp and we flag it.
SUBSTANTIVE_TOKENS = {
    "vs", "instead of", "because", "to enable", "no existing",
    "no similar", "reuse not possible", "differs from", "replaces",
    "supersedes", "complements", "specialises", "specializes",
    "bootstraps", "extends", "wraps", "adapter for", "shim for",
    "fork of", "needed for", "required by", "drives", "drive",
    "decouples", "isolates", "prevents", "forces",
    "needs review", "needs user review",
}

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class CheckError:
    file: str
    line: int  # 1-indexed; 0 if marker missing entirely
    severity: str  # "missing" | "too_short" | "not_substantive"
    reason_text: str = ""

    def render(self) -> str:
        if self.severity == "missing":
            return (
                f"  ERROR  [{self.file}]  no REASON marker at top of file. "
                f"Add as line 1 (or after shebang): "
                f"# REASON: <>={MIN_REASON_CHARS}-char justification of why "
                f"this file exists>"
            )
        if self.severity == "too_short":
            return (
                f"  ERROR  [{self.file}:{self.line}]  REASON marker is too "
                f"short ({len(self.reason_text)} chars; need >= "
                f"{MIN_REASON_CHARS}): {self.reason_text!r}"
            )
        return (
            f"  ERROR  [{self.file}:{self.line}]  REASON marker is generic "
            f"(no substantive justification token). Add one of: vs, "
            f"instead of, because, to enable, no existing, replaces, "
            f"forces, needs review. Got: {self.reason_text!r}"
        )


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


def _is_exempt_path(rel_posix: str) -> bool:
    parts = rel_posix.split("/")
    # SERIAL_OK_LOOP: path components <= ~10 deep; early-return on first match
    for p in parts:
        if p in EXEMPT_DIR_PARTS:
            return True
    if any(parts[0].startswith(pre) for pre in EXEMPT_TOP_PREFIXES):
        return True
    return False


def iter_target_files(include_tests: bool = False) -> Iterable[Path]:
    # SERIAL_OK_LOOP: os.walk is a generator with stateful pruning (we mutate
    # dirnames in-place to skip exempt subtrees); cannot be parallelised
    # without losing the prune semantics
    for current, dirnames, filenames in os.walk(REPO_ROOT):
        # Prune exempt subdirectories at the current level so os.walk
        # never descends into target/, .venv/, etc.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXEMPT_DIR_PARTS
            and not any(d.startswith(pre) for pre in EXEMPT_TOP_PREFIXES)
        ]
        # SERIAL_OK_LOOP: per-directory filename loop; bounded by files-in-dir
        for fn in filenames:
            if fn in EXEMPT_FILE_NAMES:
                continue
            ext = os.path.splitext(fn)[1]
            if ext not in SCRIPT_EXTS:
                continue
            p = Path(current) / fn
            rel = p.relative_to(REPO_ROOT).as_posix()
            if not include_tests and any(
                rel.startswith(pre) for pre in TEST_DIR_PREFIXES
            ):
                continue
            yield p


def find_reason_marker(path: Path) -> tuple[int, str] | None:
    """Read first ~30 non-blank lines of the file looking for a REASON
    marker. Returns (line_no, reason_text) or None if not found."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    lines = text.splitlines()
    is_rust = path.suffix == ".rs"
    pat = RS_MARKER_RE if is_rust else PY_SH_MARKER_RE
    comment_prefix = "//" if is_rust else "#"
    # 30-line window: a review-block header may prepend up to ~15 lines
    # (e.g. `=== LLM_REVIEW_BLOCK ===`) ahead of the REASON marker.
    max_lines_to_scan = 30
    # SERIAL_OK_LOOP: walks first ~30 lines of file looking for the REASON
    # marker; bounded by max_lines_to_scan
    for i, line in enumerate(lines[:max_lines_to_scan], start=1):
        stripped = line.strip()
        # Skip shebang and pure-blank lines (they're allowed before the marker).
        if not stripped or SHEBANG_RE.match(line):
            continue
        m = pat.match(line)
        if m:
            # Read the FULL contiguous comment block so a multi-line header
            # whose substantive token lands on a continuation line still
            # satisfies the gate. The block ends at the first non-comment
            # line OR a blank comment line. The reported line stays `i`.
            parts = [m.group("reason").strip()]
            # SERIAL_OK_LOOP: walks continuation comment lines; bounded by max_lines_to_scan
            for cont in lines[i:i + max_lines_to_scan]:
                cs = cont.strip()
                if not cs.startswith(comment_prefix):
                    break
                body = cs[len(comment_prefix):].strip()
                if not body:
                    break
                parts.append(body)
            return (i, " ".join(parts).strip())
        # Allow a docstring or comment block before the marker —
        # but not a code line. If we hit a non-comment non-string line,
        # the marker isn't at the top.
        if not (stripped.startswith("#") or stripped.startswith("//")
                or stripped.startswith("\"\"\"") or stripped.startswith("'''")
                or stripped.startswith("/*") or stripped.startswith("*")
                or stripped.startswith("\"")):
            break
    return None


def validate_file(path: Path) -> list[CheckError]:
    rel = path.relative_to(REPO_ROOT).as_posix()
    found = find_reason_marker(path)
    if found is None:
        return [CheckError(file=rel, line=0, severity="missing")]
    line_no, reason = found
    if len(reason) < MIN_REASON_CHARS:
        return [CheckError(file=rel, line=line_no, severity="too_short", reason_text=reason)]
    rl = reason.lower()
    has_substantive = any(tok in rl for tok in SUBSTANTIVE_TOKENS)
    if not has_substantive:
        return [CheckError(file=rel, line=line_no, severity="not_substantive", reason_text=reason)]
    return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify every script file (.py/.rs/.sh/.bash) has a top-of-file "
            "REASON marker explaining why it exists. Forces the AI to think "
            "about reuse-vs-create before writing new scripts."
        )
    )
    parser.add_argument(
        "files", nargs="*",
        help="Specific files to scan. If omitted, scan the whole repo.",
    )
    parser.add_argument("--json", action="store_true",
                        help="Emit a JSON report on stdout.")
    parser.add_argument("--include-tests", action="store_true",
                        help="Also scan files under tests/ (default: skipped).")
    parser.add_argument("--summary", action="store_true",
                        help="Print a per-severity summary count.")
    args = parser.parse_args(argv)

    if args.files:
        targets = []
        # SERIAL_OK_LOOP: CLI args list (typically 1-5 files); sequential resolve
        for f in args.files:
            p = Path(f)
            if not p.is_absolute():
                p = (REPO_ROOT / f).resolve()
            if not p.exists():
                # SERIAL_OK_STDOUT: CLI WARN message about a missing arg
                print(f"[check_file_reason] WARN: file not found: {f}", file=sys.stderr)
                continue
            if p.suffix not in SCRIPT_EXTS:
                continue
            if p.name in EXEMPT_FILE_NAMES:
                continue
            targets.append(p)
    else:
        targets = list(iter_target_files(include_tests=args.include_tests))

    errors: list[CheckError] = []
    # SERIAL_OK_LOOP: scans files one by one; per-file open + read first ~30
    # lines, sub-millisecond
    for p in targets:
        errors.extend(validate_file(p))

    if args.json:
        print(json.dumps({
            "ok": not errors,
            "files_scanned": len(targets),
            "errors_total": len(errors),
            "errors": [e.__dict__ for e in errors],
        }, indent=2))
        return 1 if errors else 0

    if args.summary:
        per_sev: dict[str, int] = {}
        # SERIAL_OK_LOOP: tally severities (3 categories max); single pass
        for e in errors:
            per_sev[e.severity] = per_sev.get(e.severity, 0) + 1
        print(f"[check_file_reason] {len(targets)} file(s) scanned, "
              f"{len(errors)} error(s).")
        # SERIAL_OK_LOOP: 3 severity buckets max; sequential print
        for s in sorted(per_sev):
            # SERIAL_OK_STDOUT: per-severity summary line
            print(f"  {s:18s} {per_sev[s]:5d}")
        return 1 if errors else 0

    if errors:
        print(
            f"[check_file_reason] {len(errors)} file(s) need a REASON "
            f"marker (or a better one):",
            file=sys.stderr,
        )
        # SERIAL_OK_LOOP: render error list in path-sorted order
        for e in sorted(errors, key=lambda x: x.file):
            # SERIAL_OK_STDOUT: per-error report line
            print(e.render(), file=sys.stderr)
        print(
            "\n  -> Each script must declare WHY it exists at the top via:\n"
            "      # REASON: <>=30-char justification>   (Python / shell)\n"
            "      // REASON: <>=30-char justification>  (Rust)\n"
            "  Reason should mention WHY this file exists vs reusing an\n"
            "  existing one (use words like 'vs', 'instead of', 'because',\n"
            "  'to enable', 'no existing', 'replaces', 'forces').\n"
            "\n  If genuinely uncertain, write a SPECIFIC reason that\n"
            "  includes 'needs review' (substantive token) — e.g. \"role\n"
            "  unclear after reading code; appears to wrap X but may\n"
            "  overlap with Y, needs review\". This passes the gate AND\n"
            "  surfaces the file for human review via grep.\n"
            "\n  See scripts/check_file_reason.md.",
            file=sys.stderr,
        )
        return 1

    print(f"[check_file_reason] OK — {len(targets)} file(s) all have valid REASON markers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
