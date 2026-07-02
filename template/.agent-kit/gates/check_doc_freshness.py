#!/usr/bin/env python3
# REASON: doc-drift gate — enforces folder README presence + Pass C tracks_dir cross-tree cascade + Pass D orphan-md contract (tracks_dir/frozen_at/derived_from) instead of letting docs silently rot; hosts the `--ack-no-drift PATH --reason '<msg>'` escape hatch for cascade-only mtime ripples.
"""
scripts/check_doc_freshness.py -- CI gate for doc presence + hierarchical mtime.

Three layers, all enforcing. Together they make sure that whenever any code
file changes, the corresponding folder README/index page is edited to reflect
that change (the act of editing forces a read + drift comparison):

  Pass A -- presence
    - Every committed folder (with exemptions) has a README.md or index.md

  Pass B -- hierarchical mtime, bottom-up
    - For every folder: README.md mtime >= max mtime of every child
      (file or subfolder README.md)

  Pass C -- cross-tree `tracks_dir:` cascade (session-wrap-bounded)
    - On the commit that stages a handoff (the session-wrap commit),
      a page declaring `tracks_dir: <path>` must be newer than the
      newest content file under that path. Catches "page summarises
      module X but module X just shipped 3 commits". Mid-session
      commits stage no handoff, so the cascade is silent.

  Pass D -- orphan-md contract
    - Every authored .md under docs/ must declare ONE of:
      `tracks_dir:` (living, cascade-tracked) /
      `frozen_at: <YYYY-MM-DD>` (historical snapshot) /
      `derived_from: [<path>, ...]` (PRESENTATION page, regenerated)
    - OR be in PASS_D_EXEMPT (section indexes, framework dirs).

To satisfy the gate after a code change, EDIT the folder README (and any
README the change touches). Don't bypass -- the act of editing forces you
to read the README and surface any drift the change made stale.

Errors are sorted deepest-first so leaf violations surface first.

Mtime source: filesystem `os.path.getmtime` with fallback to
`git log -1 --format=%ct -- <path>` for files that exist but have no
filesystem mtime newer than their git history (i.e. files that came
through a fresh `git clone` and never got touched in this working tree).

Usage:
  python scripts/check_doc_freshness.py
  python scripts/check_doc_freshness.py --json          # machine-readable

Exit codes:
  0 -- all consistent
  1 -- drift detected (presence missing OR mtime stale)
  2 -- config malformed

See .agent-kit/adapters/claude/README.md "Doc-drift control framework" for the design.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import yaml  # PyYAML
except ImportError:
    print(
        "[check_doc_freshness] PyYAML not installed (needed for tracks_dir parsing).\n"
        "  pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]

# ----------------------------------------------------------------------
# Config -- what counts as a script, which folders are exempt, etc.
# ----------------------------------------------------------------------

# Extensions considered "script" files (used by sibling constants kept
# for backwards compatibility with check_file_reason.py).
SCRIPT_EXTS = {".py", ".rs", ".sh", ".ts", ".js"}

SCRIPT_FILE_EXEMPT_NAMES = {
    "__init__.py",
    "conftest.py",
    "setup.py",
    "build.rs",
    "_dummy.rs",
}

# Top-level folders excluded from the entire walk. Wildcard-prefixed
# entries (`backup_*`) match by `startswith`.
TOP_LEVEL_EXEMPT_PREFIXES = (
    ".git",
    ".github",
    ".claude",
    ".agent-kit",
    ".agents",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    # AI-judge sidecar dir; regenerated on every commit, README would
    # never be "fresh enough".
    ".llm-review",
    "target",
    "venv",
    "env",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "data",
    "runs",
    "logs",
    ".idea",
    "archive",
    "backup_",  # backup_<date>/ etc.
)

# Subdirectories (anywhere in tree) excluded from walk.
ANY_DEPTH_EXEMPT_DIRS = {
    ".git",
    "__pycache__",
    "target",
    "node_modules",
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "archive",
}

# Folders specifically exempt from the README-presence rule (but still
# walked for the mtime cascade). E.g. tests/ folders, fixtures/.
README_EXEMPT_DIRS = {
    "tests",
    "fixtures",
    "test_data",
    "examples",
    "includes",
    "js",
    "css",
    "templates",
    "migrations",
    "deploy",
    "adr",
}

# Path-pattern based exempts (NOT name-based). Edit these to match your
# project's layout. Examples: crates/ sub-folders, tooling trees, etc.
README_EXEMPT_PATH_PATTERNS: tuple[re.Pattern, ...] = (
    # scripts/ subtree is tracked from .agent-kit/adapters/claude/README.md via tracks_dir,
    # so folder-level README requirement is dropped. Per-script REASON
    # headers already document purpose.
    re.compile(r"^scripts(/.*)?$"),
)

# Markdown files that DON'T need to be hierarchically-fresh (auto-generated).
MD_FRESHNESS_EXEMPT: set[str] = set()

# Frontmatter parser. A leading `---\n...---\n` block is parsed as YAML;
# everything else is plain markdown body.
_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL,
)

# Extensions a `tracks_dir:` walk considers "content" when computing
# the newest-mtime under the tracked directory.
_TRACKS_DIR_CONTENT_EXTS = {".py", ".rs", ".sh", ".ts", ".js", ".md"}


# ----------------------------------------------------------------------
# Data model
# ----------------------------------------------------------------------


@dataclass
class CheckError:
    severity: str  # "error" | "warn"
    kind: str  # "presence-readme" | "mtime-readme" | "tracks-dir" | "orphan-md"
    path: str  # relative to repo root
    detail: str
    depth: int = 0  # for sort order: deeper = larger

    def render(self) -> str:
        prefix = "ERROR" if self.severity == "error" else "WARN "
        return f"  {prefix}  [{self.kind}]  {self.path}\n         {self.detail}"


# ----------------------------------------------------------------------
# Walk + filter
# ----------------------------------------------------------------------


def is_top_level_exempt(rel_parts: tuple[str, ...]) -> bool:
    if not rel_parts:
        return False
    top = rel_parts[0]
    # SERIAL_OK_LOOP: walks exempt prefixes per call; tiny constant list
    for prefix in TOP_LEVEL_EXEMPT_PREFIXES:
        if prefix.endswith("_") and top.startswith(prefix):
            return True
        if top == prefix:
            return True
        # nested under a known toplevel-exempt path
        if "/" in prefix:
            joined = "/".join(rel_parts[: prefix.count("/") + 1])
            if joined == prefix:
                return True
    return False


def walk_repo(repo_root: Path) -> tuple[list[Path], list[Path]]:
    """Walk the repo and return (folders, files) lists.

    Excludes anything under TOP_LEVEL_EXEMPT_PREFIXES and any
    ANY_DEPTH_EXEMPT_DIRS encountered mid-walk. Skipped paths are not
    descended into.
    """
    folders: list[Path] = []
    files: list[Path] = []
    # SERIAL_OK_LOOP: os.walk is a generator with stateful pruning (we
    # mutate dirnames in-place to skip subtrees); cannot be parallelised
    # without losing the prune semantics
    for current, dirnames, filenames in os.walk(repo_root):
        cur_path = Path(current)
        rel = cur_path.relative_to(repo_root).as_posix()
        rel_parts = tuple(p for p in rel.split("/") if p) if rel != "." else ()

        # Skip if the parent dir is exempt.
        if is_top_level_exempt(rel_parts):
            dirnames[:] = []  # don't descend further
            continue
        if any(p in ANY_DEPTH_EXEMPT_DIRS for p in rel_parts):
            dirnames[:] = []
            continue

        # Prune subdirectories that are themselves exempt.
        dirnames[:] = [
            d
            for d in dirnames
            if d not in ANY_DEPTH_EXEMPT_DIRS
            and not is_top_level_exempt(rel_parts + (d,))
        ]

        if rel_parts:
            folders.append(cur_path)
        # SERIAL_OK_LOOP: filenames in current dir; collects into shared list
        for fn in filenames:
            files.append(cur_path / fn)
    return folders, files


# ----------------------------------------------------------------------
# Mtime
# ----------------------------------------------------------------------


# Per-path commit timestamp comes from the shared helper.
import importlib.util as _ilu

_HELPER_SPEC = _ilu.spec_from_file_location(
    "_git_mtime", Path(__file__).resolve().parent / "_git_mtime.py"
)
assert _HELPER_SPEC is not None and _HELPER_SPEC.loader is not None
_GIT_MTIME = _ilu.module_from_spec(_HELPER_SPEC)
sys.modules["_git_mtime"] = _GIT_MTIME
_HELPER_SPEC.loader.exec_module(_GIT_MTIME)


def effective_mtime(path: Path, repo_root: Path) -> float:
    return _GIT_MTIME.effective_mtime(path, repo_root)


# ----------------------------------------------------------------------
# Cross-tree dependency: `tracks_dir:` frontmatter
# ----------------------------------------------------------------------


def parse_tracks_dir(md_path: Path) -> list[str]:
    """Read `.md` frontmatter and return a list of `tracks_dir:` values
    (repo-relative posix paths). Returns `[]` for pages without the
    field.

    Accepted shapes in YAML:

        tracks_dir: src/
        tracks_dir:
          - src/
          - lib/
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    try:
        body = yaml.safe_load(m.group("body"))
    except yaml.YAMLError:
        return []
    if not isinstance(body, dict):
        return []
    raw = body.get("tracks_dir")
    if raw is None:
        return []
    if isinstance(raw, str):
        candidates = [raw]
    elif isinstance(raw, list):
        candidates = [str(x) for x in raw if isinstance(x, str)]
    else:
        return []
    # Normalise: strip trailing slash, posix path.
    return [c.rstrip("/") for c in candidates if c.strip()]


def newest_content_mtime(
    tracked_root: Path,
    repo_root: Path,
    cache: dict[Path, float],
) -> tuple[float, Path | None]:
    """Walk `tracked_root` and return `(newest_mtime, newest_path)` over
    every content file beneath it (recursive), respecting the same
    exemption set as the main walk. Returns `(0.0, None)` for an empty
    tree.

    Used by the cross-tree `tracks_dir:` cascade -- when ANY content file
    under a tracked directory is newer than the tracking page, the page
    must be re-read + edited.
    """
    newest_ts = 0.0
    newest_path: Path | None = None
    if not tracked_root.exists() or not tracked_root.is_dir():
        return (newest_ts, newest_path)
    # SERIAL_OK_LOOP: os.walk is a generator with stateful pruning (we
    # mutate dirnames in-place); cannot parallelise without losing prune
    # semantics. The top-level exemption filter is NOT applied here --
    # a caller asking for `tracks_dir: .claude/handoffs/` has opted in
    # to scanning that root.
    for current, dirnames, filenames in os.walk(tracked_root):
        # Prune ANY_DEPTH_EXEMPT_DIRS subdirectories at this level.
        dirnames[:] = [d for d in dirnames if d not in ANY_DEPTH_EXEMPT_DIRS]
        # SERIAL_OK_LOOP: per-directory filename loop (typically <= 50)
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext not in _TRACKS_DIR_CONTENT_EXTS:
                continue
            f = Path(current) / fn
            if f not in cache:
                cache[f] = effective_mtime(f, repo_root)
            ts = cache[f]
            if ts > newest_ts:
                newest_ts = ts
                newest_path = f
    return (newest_ts, newest_path)


def handoff_in_staged_commit(repo_root: Path) -> bool:
    """True iff the commit being created stages a session handoff
    (`.claude/handoffs/handoff_*.md`).

    Pass C is the session-wrap cascade -- it must fire on exactly one
    commit per session: the one the session-wrap flow makes, when the AI
    has context loaded to reconcile drift.

    `git diff --cached` is empty outside a commit (a manual run or the
    canary's direct call), so Pass C is correctly silent there too --
    the gate enforces at commit time."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root, capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if r.returncode != 0:
        return False
    # SERIAL_OK_LOOP: per-staged-path scan; the staged set is small
    for line in r.stdout.splitlines():
        p = line.strip().replace("\\", "/")
        name = p.rsplit("/", 1)[-1]
        if (
            p.startswith(".claude/handoffs/")
            and name.startswith("handoff_")
            and name.endswith(".md")
        ):
            return True
    return False


def check_tracks_dir(
    files: list[Path],
    repo_root: Path,
    mtime_cache: dict[Path, float],
) -> list[CheckError]:
    """Pass C -- cross-tree dependency (session-bounded).

    For every authored `.md` whose frontmatter declares
    `tracks_dir: <path>` (single or list), the cascade fires when BOTH
    conditions hold:

      1. The current commit stages a session handoff
         (`.claude/handoffs/handoff_*.md`) -- i.e. this IS the
         session-wrap commit (`handoff_in_staged_commit`).
      2. The tracking page's mtime is < the newest content mtime under
         any tracked directory (tracked content drifted since the .md's
         last update).

    Both conditions = AND. A mid-session code commit stages no handoff,
    so condition 1 is false and the whole pass no-ops -- the AI iterates
    unburdened. The cascade surfaces drift on exactly the session-wrap
    commit, when the AI has context loaded to reconcile docs.
    """
    errors: list[CheckError] = []
    # Condition 1: fire only on the commit that writes a handoff. A
    # mid-session commit stages no handoff -> Pass C is silent.
    if not handoff_in_staged_commit(repo_root):
        return errors
    # SERIAL_OK_LOOP: per-.md frontmatter scan; yaml parsing is
    # microsecond per file
    for f in files:
        if f.suffix != ".md":
            continue
        rel = f.relative_to(repo_root).as_posix()
        if any(rel.startswith(p) for p in TRACKS_DIR_PATH_EXEMPT_PREFIXES):
            continue
        targets = parse_tracks_dir(f)
        if not targets:
            continue
        page_mtime = mtime_cache.get(f) or effective_mtime(f, repo_root)
        mtime_cache[f] = page_mtime
        # SERIAL_OK_LOOP: walks the (typ <= 3) tracked dirs declared by
        # this page; each delegates to newest_content_mtime
        for target in targets:
            tracked = (repo_root / target).resolve()
            child_mtime, child_path = newest_content_mtime(
                tracked, repo_root, mtime_cache
            )
            if page_mtime < child_mtime:
                rel_page = f.relative_to(repo_root).as_posix()
                child_label = (
                    str(child_path.relative_to(repo_root))
                    if child_path
                    else target
                )
                errors.append(
                    CheckError(
                        severity="error",
                        kind="tracks-dir",
                        path=rel_page,
                        detail=(
                            f"declares `tracks_dir: {target}` but page "
                            f"is older than newest tracked file "
                            f"{child_label}, and this commit stages a "
                            f"handoff (session-wrap) -- reconcile the "
                            f"doc body against the tracked drift."
                        ),
                        depth=len(f.parts),
                    )
                )
    return errors


# ----------------------------------------------------------------------
# Pass D -- authored .md coverage (every doc page must declare its
# maintenance contract, OR be in the explicit exemption set)
# ----------------------------------------------------------------------

# Pass D EXEMPT path patterns (relative to repo root, posix).
# Any docs/**/*.md whose relative path matches one of these is exempt
# from the "must declare tracks_dir or frozen_at" rule.
PASS_D_EXEMPT_NAMES = {"index.md", "README.md"}
PASS_D_EXEMPT_PREFIXES = (
    "docs/archive/",    # archived
    "docs/includes/",   # partials / abbreviations
)

# Pass C `tracks_dir:` cascade exemption: pages owned by a build tool
# are rebuilt from authored sources during build, not per-commit. Their
# `tracks_dir:` declarations stay as rebuild-source hints; per-commit
# cascades are skipped.
# Edit this list to match your project's generated-content directories.
TRACKS_DIR_PATH_EXEMPT_PREFIXES: tuple[str, ...] = ()


def parse_frozen_at(md_path: Path) -> str | None:
    """Read .md frontmatter, return the `frozen_at:` value or None."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        body = yaml.safe_load(m.group("body"))
    except yaml.YAMLError:
        return None
    if not isinstance(body, dict):
        return None
    val = body.get("frozen_at")
    return str(val) if val is not None else None


def parse_derived_from(md_path: Path) -> list[str]:
    """Read .md frontmatter, return the `derived_from:` list or [].

    Pages with `derived_from:` are PRESENTATION pages -- regenerated by
    a build tool from the listed source-of-truth pages, not hand-maintained.
    They are exempt from Pass D's "must declare a maintenance contract"
    rule: the contract IS the `derived_from:` list.
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return []
    try:
        body = yaml.safe_load(m.group("body"))
    except yaml.YAMLError:
        return []
    if not isinstance(body, dict):
        return []
    raw = body.get("derived_from")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(x) for x in raw if isinstance(x, str)]
    return []


def check_authored_md_coverage(
    files: list[Path],
    repo_root: Path,
) -> list[CheckError]:
    """Pass D -- every authored .md under docs/ must declare a maintenance
    contract: `tracks_dir:` (cascade dependency), `frozen_at:` (historical
    snapshot), `derived_from:` (PRESENTATION page regenerated from sources),
    OR be in PASS_D_EXEMPT (auto-gen / framework / nav).

    Catches orphan pages -- content with no clear ownership that gets stale
    silently because nothing forces it to be updated.
    """
    errors: list[CheckError] = []
    # SERIAL_OK_LOOP: bounded by len(files); per-file frontmatter parse +
    # path-prefix check
    for f in files:
        if f.suffix != ".md":
            continue
        try:
            rel = f.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        # Pass D scope: only docs/ tree.
        if not rel.startswith("docs/"):
            continue
        # Exempt by filename (any **/index.md is nav).
        if f.name in PASS_D_EXEMPT_NAMES:
            continue
        # Exempt by path prefix (auto-gen, framework, mirrors, etc.).
        if any(rel.startswith(p) for p in PASS_D_EXEMPT_PREFIXES):
            continue
        # Required: tracks_dir OR frozen_at OR derived_from.
        tracks = parse_tracks_dir(f)
        frozen = parse_frozen_at(f)
        derived = parse_derived_from(f)
        if tracks or frozen or derived:
            continue
        errors.append(
            CheckError(
                severity="error",
                kind="orphan-md",
                path=rel,
                detail=(
                    "authored .md has no maintenance contract. Add ONE of:\n"
                    "         - `tracks_dir: [<path>, ...]` in frontmatter (cascade-tracked living doc)\n"
                    "         - `frozen_at: <YYYY-MM-DD>` in frontmatter (historical snapshot, intentionally not maintained)\n"
                    "         - `derived_from: [<path>, ...]` in frontmatter (PRESENTATION page, regenerated from listed sources)\n"
                    "         - move the file under archive/ if it's retired"
                ),
                depth=len(f.parts),
            )
        )
    return errors


# ----------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------


def check_presence(
    folders: list[Path],
    files: list[Path],
    repo_root: Path,
) -> list[CheckError]:
    """Pass A -- every folder has README, every script file has sibling .md."""
    errors: list[CheckError] = []

    # Every committed folder has README.md OR index.md (with exemptions).
    # index.md is the section-index convention; either satisfies the
    # "folder summary" rule.
    # SERIAL_OK_LOOP: walks every repo folder once; bounded by repo size;
    # file-existence checks are cheap stat calls
    for folder in folders:
        rel = folder.relative_to(repo_root).as_posix()
        if folder.name in README_EXEMPT_DIRS:
            continue
        if any(p.match(rel) for p in README_EXEMPT_PATH_PATTERNS):
            continue
        readme = folder / "README.md"
        index = folder / "index.md"
        if not readme.exists() and not index.exists():
            errors.append(
                CheckError(
                    severity="error",
                    kind="presence-readme",
                    path=rel + "/",
                    detail="folder is missing README.md or index.md "
                    "(add a short summary file or exempt the folder name "
                    "in scripts/check_doc_freshness.py)",
                    depth=len(folder.parts),
                )
            )

    return errors


def check_freshness(
    folders: list[Path],
    files: list[Path],
    repo_root: Path,
) -> list[CheckError]:
    """Pass B -- hierarchical mtime, bottom-up."""
    errors: list[CheckError] = []

    # Build folder -> children map for hierarchy walk.
    folder_set = set(folders)
    by_parent: dict[Path, list[Path]] = {f: [] for f in folder_set}
    by_parent[repo_root] = []
    # SERIAL_OK_LOOP: builds parent->children map; one append per file
    for f in files:
        parent = f.parent
        by_parent.setdefault(parent, []).append(f)
    # SERIAL_OK_LOOP: builds parent->children map; one append per folder
    for d in folders:
        parent = d.parent
        by_parent.setdefault(parent, []).append(d)

    # Pre-compute mtime of every file we care about (cache).
    mtime_cache: dict[Path, float] = {}

    def mtime(p: Path) -> float:
        if p not in mtime_cache:
            mtime_cache[p] = effective_mtime(p, repo_root)
        return mtime_cache[p]

    # ---- Pass B: folder README vs children mtime ----
    # Sort folders deepest-first so by the time we evaluate a parent
    # its children's effective mtimes have been resolved.
    folders_deep_first = sorted(
        folders, key=lambda p: len(p.parts), reverse=True
    )

    folder_eff_mtime: dict[Path, float] = {}

    # SERIAL_OK_LOOP: deepest-first walk so child folder_eff_mtime is
    # populated before parent reads it; cannot be parallelised -- direct
    # dependency chain
    def _child_mtime(c: Path) -> float | None:
        """Return effective mtime of a child for parent-folder freshness
        computation, OR None if the child should be ignored (auto-generated
        doc)."""
        try:
            c_rel = c.relative_to(repo_root).as_posix()
        except ValueError:
            c_rel = ""
        if c_rel in MD_FRESHNESS_EXEMPT:
            return None
        return folder_eff_mtime.get(c, mtime(c))

    # SERIAL_OK_LOOP: deepest-first folder iteration so children's
    # eff_mtime is ready before parents read it; sequential by direct
    # data dependency
    for folder in folders_deep_first:
        rel = folder.relative_to(repo_root).as_posix() if folder != repo_root else ""
        if folder.name in README_EXEMPT_DIRS or any(p.match(rel) for p in README_EXEMPT_PATH_PATTERNS):
            children = by_parent.get(folder, [])
            child_mtimes = [m for m in (_child_mtime(c) for c in children) if m is not None] or [0.0]
            folder_eff_mtime[folder] = max(child_mtimes)
            continue

        # Pick the folder summary file: README.md only. index.md is a
        # section-landing page (presentation), not a folder-tracking
        # summary -- cascading mtime onto it produces noise edits every
        # time anything below the folder is touched. Pass A (presence)
        # still accepts index.md as satisfying "folder has a summary".
        readme_candidate = folder / "README.md"
        if readme_candidate.exists():
            summary = readme_candidate
        else:
            # No README.md: skip mtime-readme check for this folder.
            # Effective mtime still bubbles up so the parent's cascade is honest.
            children = by_parent.get(folder, [])
            child_mtimes = [m for m in (_child_mtime(c) for c in children) if m is not None] or [0.0]
            folder_eff_mtime[folder] = max(child_mtimes)
            continue

        summary_mtime = mtime(summary)
        children = by_parent.get(folder, [])
        max_child = 0.0
        max_child_path: Path | None = None
        # SERIAL_OK_LOOP: scans this folder's children for newest-mtime;
        # small N per folder, sequential is fine
        for c in children:
            if c == summary:
                continue
            cm = _child_mtime(c)
            if cm is None:
                continue
            if cm > max_child:
                max_child = cm
                max_child_path = c

        # Strict mtime comparison -- no tolerance window.
        if summary_mtime < max_child:
            rel_summary = summary.relative_to(repo_root).as_posix()
            child_label = (
                str(max_child_path.relative_to(repo_root))
                if max_child_path
                else "<a child>"
            )
            errors.append(
                CheckError(
                    severity="error",
                    kind="mtime-readme",
                    path=rel_summary,
                    detail=(
                        f"{summary.name} is older than newest child "
                        f"{child_label}."
                    ),
                    depth=len(folder.parts),
                )
            )

        # Folder's effective mtime bubbles MAX(summary, max_child) upward.
        folder_eff_mtime[folder] = max(summary_mtime, max_child)

    return errors


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

# Substantive tokens for --ack-no-drift --reason validation. Mirrors the
# spirit of check_file_reason.py's REASON-marker tokens but specialised
# for "I read the page top-to-bottom and it has no body drift related to
# the cascade fire". Vague reasons like "minor change" or "fix" do not
# pass -- the operator must name what they checked or why no drift exists.
_ACK_REASON_TOKENS = (
    "vs",
    "because",
    "unrelated",
    "no impact",
    "cascade ripple",
    "read top-to-bottom",
    "confirmed",
    "no body drift",
    "orthogonal",
    "off-topic",
    "no schema change",
    "no architectural",
)
_ACK_REASON_MIN_CHARS = 30


def _validate_ack_reason(reason: str) -> str | None:
    """Return None if valid, or an error message string."""
    r = (reason or "").strip()
    if len(r) < _ACK_REASON_MIN_CHARS:
        return (
            f"--reason too short ({len(r)} chars, need >={_ACK_REASON_MIN_CHARS}); "
            "explain what you checked + why no drift exists"
        )
    rl = r.lower()
    if not any(tok in rl for tok in _ACK_REASON_TOKENS):
        return (
            "--reason missing a substantive token; include one of: "
            + ", ".join(repr(t) for t in _ACK_REASON_TOKENS)
        )
    return None


def _handle_ack_no_drift(paths: list[str], reason: str) -> int:
    """Touch each path's mtime forward + append an audit log row.

    Used to clear cascade-only fires on pages that genuinely have no body
    drift related to the trigger. Logs to `docs/_facts/no_drift_acks.log`
    so post-hoc audits can review whether the acks were appropriate.
    Returns 0 on success, 1 on validation/IO failure.
    """
    err = _validate_ack_reason(reason)
    if err is not None:
        print(f"[check_doc_freshness] --ack-no-drift refused: {err}", file=sys.stderr)
        return 1

    log_path = REPO_ROOT / "docs" / "_facts" / "no_drift_acks.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    bumped: list[Path] = []
    failures: list[str] = []
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute():
            p = (REPO_ROOT / raw).resolve()
        else:
            p = p.resolve()
        if not p.exists():
            failures.append(f"path not found: {raw}")
            continue
        try:
            os.utime(p, None)  # bump mtime (and atime) to now
            bumped.append(p)
        except OSError as e:
            failures.append(f"os.utime({raw}) failed: {e}")

    if bumped:
        ts_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            with log_path.open("a", encoding="utf-8") as f:
                for p in bumped:
                    rel = p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else p.as_posix()
                    f.write(f"{ts_iso}\t{rel}\t{reason.strip()}\n")
        except OSError as e:
            failures.append(f"log append failed: {e}")

    if bumped:
        print(
            f"[check_doc_freshness] --ack-no-drift: bumped {len(bumped)} path(s) -- "
            f"logged to {log_path.relative_to(REPO_ROOT).as_posix()}",
            file=sys.stderr,
        )
        for p in bumped:
            rel = p.relative_to(REPO_ROOT).as_posix() if p.is_relative_to(REPO_ROOT) else p.as_posix()
            print(f"  - {rel}", file=sys.stderr)

    if failures:
        for msg in failures:
            print(f"[check_doc_freshness] --ack-no-drift WARNING: {msg}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify every folder has README/index, the mtime "
        "hierarchy is satisfied, tracks_dir cascade is fresh, and every "
        "authored docs/*.md declares a maintenance contract "
        "(tracks_dir / frozen_at / derived_from)."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON report on stdout.",
    )
    parser.add_argument(
        "--ack-no-drift",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Acknowledge that PATH has been read top-to-bottom and contains "
            "NO body drift related to the cascade fire -- bump its mtime to "
            "now. Use ONLY for cascade ripples on pages genuinely unrelated "
            "to the change. Requires --reason with a substantive token. "
            "Repeat the flag for multiple paths. The acknowledgement is "
            "logged to docs/_facts/no_drift_acks.log for post-hoc audit. "
            "DO NOT use to skip real drift work."
        ),
    )
    parser.add_argument(
        "--reason",
        default="",
        help=(
            "Required with --ack-no-drift. >=30 chars + a substantive token "
            "(`vs`, `because`, `unrelated`, `no impact`, `cascade ripple`, "
            "`read top-to-bottom`, `confirmed`). The reason is logged for "
            "audit; vague reasons fail the validation."
        ),
    )
    args = parser.parse_args(argv)

    if args.ack_no_drift:
        return _handle_ack_no_drift(args.ack_no_drift, args.reason)

    # Iterate-unburdened model (issue #2): ALL passes reconcile at the session-wrap
    # commit (the one staging .claude/handoffs/handoff_*.md) -- a mid-session commit
    # is never blocked on doc drift. Manual audit paths still run in full: --json,
    # or AGENT_KIT_DOC_FRESHNESS_ALWAYS=1 to enforce on every commit.
    if (
        not args.json
        and os.environ.get("AGENT_KIT_DOC_FRESHNESS_ALWAYS") != "1"
        and not handoff_in_staged_commit(REPO_ROOT)
    ):
        print(
            "[check_doc_freshness] no handoff staged -- doc drift reconciles at "
            "session-wrap (pass; audit any time with --json)."
        )
        return 0

    folders, files = walk_repo(REPO_ROOT)

    # Shared mtime cache so check_freshness + check_tracks_dir don't
    # re-read the same files twice (each file's git-log call costs a
    # subprocess).
    shared_cache: dict[Path, float] = {}

    tracks_errors = check_tracks_dir(files, REPO_ROOT, shared_cache)
    coverage_errors = check_authored_md_coverage(files, REPO_ROOT)
    all_errors = tracks_errors + coverage_errors

    # Sort deepest-first so leaf violations surface first.
    all_errors.sort(key=lambda e: (-e.depth, e.path))

    if args.json:
        print(
            json.dumps(
                {
                    "ok": not all_errors,
                    "folders_count": len(folders),
                    "files_count": len(files),
                    "errors": [
                        {
                            "severity": e.severity,
                            "kind": e.kind,
                            "path": e.path,
                            "detail": e.detail,
                            "depth": e.depth,
                        }
                        for e in all_errors
                    ],
                },
                indent=2,
            )
        )
        return 0 if not all_errors else 1

    if all_errors:
        # Discipline block printed at BOTH top AND bottom of the error
        # report. Top survives `head -N` truncation; bottom survives
        # `tail -N` truncation.
        discipline = (
            "============================================================\n"
            "  DISCIPLINE -- read BEFORE editing any .md:\n"
            "  1. tracks-dir error fires when BOTH: (a) a file in the .md's `tracks_dir:` is newer than the .md, AND (b) this commit stages a handoff_*.md (a session-wrap commit). Mid-session commits stage no handoff and never fire this. It's session-wrap time: open the changed file (named in the error detail), read it, compare against every WHY-claim / decision / current-state / gotcha in the .md, REWRITE the parts that drift. Multiple drifted docs at once? Launch parallel agents.\n"
            "  2. orphan-md error: a .md lacks one of `tracks_dir:` / `frozen_at:` / `derived_from:` in its frontmatter. Add the appropriate contract field -- `tracks_dir:` for cascade-tracked living docs, `frozen_at: YYYY-MM-DD` for snapshots.\n"
            "  3. Escape hatch: `--ack-no-drift PATH --reason '<>=30 chars>'` ONLY when the .md has been read top-to-bottom AND you've genuinely confirmed no body claim is affected by the cascade trigger. Audit-logged to `docs/_facts/no_drift_acks.log`.\n"
            "  4. NEVER: `--no-verify`, `--skip-hooks`, `--warn-only`, `--bootstrap`, `--provisional-ok`, or sentinel-only edits.\n"
            "  5. Code is source of truth for HOW; .md is source of truth for WHY / current-state / decisions. Don't enumerate counts/versions/inventories in .md bodies -- those go stale. Discovery is filesystem + frontmatter.\n"
            "  6. Each fast win NOW becomes structural pain LATER -- stale text reaches next session, gets trusted, gets built on, eventually rots half the file.\n"
            "  7. Take the slow path. Hard work takes time and the user knows it. The gate fires when something genuinely needs your attention.\n"
            "============================================================"
        )
        # TOP -- survives `head -N`
        print(discipline, file=sys.stderr)
        print(
            f"\n[check_doc_freshness] {len(all_errors)} issue(s) "
            f"across {len(folders)} folder(s) and {len(files)} file(s):",
            file=sys.stderr,
        )
        # SERIAL_OK_LOOP: render each error line in deepest-first sort order
        for e in all_errors:
            # SERIAL_OK_STDOUT: per-error report line
            print(e.render(), file=sys.stderr)
        # BOTTOM -- survives `tail -N`. Same content as top.
        print(discipline, file=sys.stderr)
        return 1

    print(
        f"[check_doc_freshness] OK -- {len(folders)} folder(s), "
        f"{len(files)} file(s) all fresh."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
