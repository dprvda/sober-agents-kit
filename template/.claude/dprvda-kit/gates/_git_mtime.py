#!/usr/bin/env python3
# REASON: shared per-path commit-timestamp loader for doc-drift gates (check_doc_freshness, etc.); one implementation, one bug surface instead of duplicated _load_git_batch helpers that historically drifted into silent-failure mode.
"""
scripts/_git_mtime.py -- shared "per-path latest-commit timestamp" helper.

One bulk `git log --pretty=format:'@@%ct@@' --name-only` walks the current
branch's history and fills a per-path cache. The `@@<ts>@@` marker
disambiguates timestamps from filenames -- paths in this repo can't start
with `@@`, so the parser is a simple two-state lexer with no ambiguity.

Why this module exists
----------------------

Multiple gates need "when was the most recent commit touching <path>?". Each
used to carry its own copy-pasted `_load_git_batch` + `_git_commit_ts` +
`_GIT_TS_CACHE`. Duplicated copies drift independently and a bug in the
shared logic (e.g. `text.split("\\n")` not splitting on NULs) is present in
ALL copies simultaneously -- both gates silently pass spuriously until caught.

Single source of truth here. Future gates needing per-path commit ts
must `from _git_mtime import git_commit_ts, effective_mtime`.

Behaviour notes
---------------

- Walks HEAD only, not `--all`. `--all` pollutes the cache with paths
  that exist only on sister branches and adds zero value for "latest
  commit on the default branch that touched <path>".
- First-write-wins: since `git log` is reverse-chronological, the
  first commit a path appears in is its most recent.
- Cache is module-global. Call `reset()` in tests / when REPO_ROOT
  changes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

# Module-global cache. Tests reset via reset().
_GIT_TS_CACHE: dict[str, int] = {}
_GIT_BATCH_LOADED: bool = False
_LAST_REPO_ROOT: Path | None = None


def reset() -> None:
    """Drop the cache and force the next call to re-run `git log`.

    Call this from tests after monkeypatching REPO_ROOT, or whenever the
    repo state changed underneath in a way the cache wouldn't see (a
    fresh commit, a worktree switch, etc.).
    """
    global _GIT_BATCH_LOADED, _LAST_REPO_ROOT
    _GIT_TS_CACHE.clear()
    _GIT_BATCH_LOADED = False
    _LAST_REPO_ROOT = None


def _load(repo_root: Path) -> None:
    """Bulk-load per-path commit timestamps for `repo_root`.

    No-op if already loaded for the same repo_root. If repo_root
    changed since the last load (e.g. a test running against a tmp
    repo), the cache is reset first.
    """
    global _GIT_BATCH_LOADED, _LAST_REPO_ROOT
    if _GIT_BATCH_LOADED and _LAST_REPO_ROOT == repo_root:
        return
    if _LAST_REPO_ROOT is not None and _LAST_REPO_ROOT != repo_root:
        _GIT_TS_CACHE.clear()
    _GIT_BATCH_LOADED = True
    _LAST_REPO_ROOT = repo_root
    try:
        out = subprocess.run(
            ["git", "log", "--pretty=format:@@%ct@@", "--name-only"],
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            timeout=30,
        )
        if out.returncode != 0:
            return
        cur_ts: int | None = None
        # SERIAL_OK_LOOP: state-machine parse of git-log output (timestamp
        # markers interleaved with paths); single pass required to associate
        # each ts with its commit's files. First-write-wins because git log
        # is newest-first.
        for raw in out.stdout.split("\n"):
            line = raw.strip()
            if not line:
                continue
            if line.startswith("@@") and line.endswith("@@") and len(line) >= 5:
                inner = line[2:-2]
                try:
                    cur_ts = int(inner)
                except ValueError:
                    cur_ts = None
                continue
            if cur_ts is not None and line not in _GIT_TS_CACHE:
                _GIT_TS_CACHE[line] = cur_ts
    except (subprocess.SubprocessError, OSError, ValueError):
        # Best-effort: if git is missing or the repo is broken, gates
        # fall back to filesystem mtime alone.
        pass


def git_commit_ts(rel_path: str, repo_root: Path) -> int | None:
    """Most-recent commit timestamp on the current branch that touched
    `rel_path`. Returns None if the path is untracked.

    `rel_path` must be the path relative to `repo_root` using forward
    slashes (POSIX form). Use `Path.relative_to(repo_root).as_posix()`.
    """
    _load(repo_root)
    # `dict.get(...)` already returns None when the key is absent, so just
    # return whatever it gave us -- preserves `0` when (extremely rarely) a
    # commit timestamp is exactly the Unix epoch.
    return _GIT_TS_CACHE.get(rel_path)


def effective_mtime(path: Path, repo_root: Path) -> float:
    """Filesystem mtime, with git-commit-time as a floor.

    Returns `max(fs_mtime, git_commit_ts)` so that:
      - Working-tree edits (which bump fs_mtime) are always seen.
      - A fresh `git clone` (where every fs_mtime gets reset to clone
        time) still sees the right "this file was meaningfully changed
        at <commit ts>" floor.
    """
    try:
        fs_mtime = path.stat().st_mtime
    except OSError:
        return 0.0
    try:
        rel = path.relative_to(repo_root).as_posix()
    except ValueError:
        # Path is outside repo_root. Caller's bug; fall back to fs.
        return fs_mtime
    git_ts = git_commit_ts(rel, repo_root)
    if git_ts is not None:
        return max(fs_mtime, float(git_ts))
    return fs_mtime
