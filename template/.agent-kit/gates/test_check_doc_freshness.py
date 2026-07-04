#!/usr/bin/env python3
# REASON: canary self-test for scripts/check_doc_freshness.py -- replaces hand-checking of gate behaviour after refactors; forces every gate-source change to re-prove that folder-README presence + mtime hierarchy + tracks cascade (file + dir entries) + Pass D (tracks / frozen_at / derived_from, with deprecated tracks_dir/tracks_file rejection) all still fire correctly.
"""
Canary self-test for `scripts/check_doc_freshness.py`.

Verifies the freshness gate enforces what it claims, end-to-end, against
a tmp git repo. Companion to test_check_staleness.py (if present) -- they
share the same `_git_mtime` helper, so a regression in either is caught here.

Cases:
  0. **sibling rule OFF** -- naked source.rs (no sibling .md) and stale
     foo.md (older than foo.rs) MUST produce ZERO `presence-md` /
     `mtime-md` errors. Regression guard: if anyone introduces a sibling
     rule, this canary fails.
  3. **mtime-readme cascade** -- a child file newer than its folder
     README MUST produce a `mtime-readme` error. Locks the bottom-up
     hierarchy enforcement.
  5. **presence-readme missing** -- a folder with content but no README/
     index MUST produce a `presence-readme` error.

Runs as `python scripts/test_check_doc_freshness.py`. Exits 0 on pass,
1 on fail. Pre-commit re-runs whenever check_doc_freshness.py,
_git_mtime.py, or this file changes -- so any future edit to the gate
or the shared helper re-validates the contract.

No pytest dependency. Self-contained.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd), env=env, check=True, capture_output=True)


def _git_init(repo: Path) -> None:
    _run(["git", "init", "-q", "-b", "main"], repo)
    _run(["git", "config", "user.email", "canary@test.local"], repo)
    _run(["git", "config", "user.name", "canary"], repo)
    _run(["git", "config", "commit.gpgsign", "false"], repo)


def _commit_at(
    repo: Path, file_rel: str, age_hours: float, content: str = "x"
) -> int:
    """Write + add + commit `file_rel` with author/committer date set to
    `age_hours` ago, and FS mtime backdated to match. Returns the ts."""
    full = repo / file_rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    ts = int(time.time() - age_hours * 3600)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = str(ts)
    env["GIT_COMMITTER_DATE"] = str(ts)
    _run(["git", "add", file_rel], repo, env=env)
    _run(
        ["git", "commit", "-q", "-m", f"add {file_rel} ({age_hours}h ago)"],
        repo,
        env=env,
    )
    os.utime(full, (ts, ts))
    return ts


def _stage(repo: Path, file_rel: str, content: str = "x") -> None:
    """Write + `git add` `file_rel` WITHOUT committing -- leaves it in
    the staged set so `git diff --cached --name-only` sees it. Used to
    simulate the in-flight commit Pass C (`handoff_in_staged_commit`)
    inspects."""
    full = repo / file_rel
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    _run(["git", "add", file_rel], repo)


def _load_module():
    """Import check_doc_freshness via sys.path so dataclasses + type
    machinery resolve `cls.__module__` correctly."""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import check_doc_freshness  # type: ignore[import-not-found]
    return check_doc_freshness


def _run_gate(cdf, repo: Path):
    """Run the gate's passes against repo. Returns the combined
    error list. Reset the shared git-mtime cache so the helper sees
    the tmp repo, not the surrounding clone."""
    cdf._GIT_MTIME.reset()
    folders, files = cdf.walk_repo(repo)
    cache: dict = {}
    return (
        cdf.check_presence(folders, files, repo)
        + cdf.check_freshness(folders, files, repo)
        + cdf.check_tracks(files, repo, cache)
        + cdf.check_authored_md_coverage(files, repo)
    )


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def main() -> int:
    cdf = _load_module()
    failures: list[str] = []

    # --- Case 0: sibling rule OFF (regression guard) -------------------
    # With foo.rs newer than its stale foo.md, AND a separate naked bar.rs
    # with no sibling at all, the gate must produce ZERO presence-md /
    # mtime-md errors. If anyone introduces the rule, this canary fails.
    with tempfile.TemporaryDirectory(prefix="cdf_canary_no_sibling_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        # foo.rs + stale foo.md (would have been mtime-md drift if rule existed).
        _commit_at(repo, "src/foo.rs", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/foo.md", age_hours=13.0, content="# foo")
        # Naked bar.rs (would have been presence-md if rule existed).
        _commit_at(repo, "src/bar.rs", age_hours=13.0, content="// bar")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")

        # Now make foo.rs newer than foo.md -- if the sibling rule existed
        # this would fire mtime-md. Post-retirement: nothing fires.
        time.sleep(1.1)
        _commit_at(repo, "src/foo.rs", age_hours=0.0, content="// v2")
        # Folder README needs to be at least as new as the touched .rs
        # to satisfy Pass B (mtime-readme cascade). Bump it together.
        _commit_at(repo, "src/README.md", age_hours=0.0, content="# src v2")
        _commit_at(repo, "README.md", age_hours=0.0, content="# repo v2")

        errs = _run_gate(cdf, repo)
        sibling_kinds = {(e.kind, e.path) for e in errs if e.kind in ("presence-md", "mtime-md")}
        if sibling_kinds:
            failures.append(
                "Case 0 FAIL: the gate produced sibling errors "
                "(presence-md or mtime-md). A per-source-file sibling rule "
                "is not part of this scaffold -- remove it. "
                f"Sibling errors: {sorted(sibling_kinds)}"
            )

    # --- Case 3: mtime-readme -- child newer than folder README ---------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_readme_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        # Establish a clean tree at 13h ago.
        _commit_at(repo, "src/foo.rs", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/foo.md", age_hours=13.0, content="# foo v1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")

        # Update BOTH foo.rs and foo.md fresh -- sibling clean, but parent
        # README left stale. mtime-readme MUST fire on src/README.md.
        time.sleep(1.1)
        _commit_at(repo, "src/foo.rs", age_hours=0.0, content="// v2")
        _commit_at(repo, "src/foo.md", age_hours=0.0, content="# foo v2")

        errs = _run_gate(cdf, repo)
        kinds = {(e.kind, e.path) for e in errs}
        if not any(
            k == "mtime-readme" and "src/README.md" in p.replace("\\", "/")
            for k, p in kinds
        ):
            failures.append(
                "Case 3 FAIL: child newer than folder README did NOT "
                "trigger mtime-readme. Bottom-up hierarchy is broken. "
                f"Errors: {sorted(kinds)}"
            )

    # --- Case 5: presence-readme missing -------------------------------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_presence_readme_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        # src/ has files but no README/index.
        _commit_at(repo, "src/foo.rs", age_hours=1.0, content="// v1")
        _commit_at(repo, "README.md", age_hours=1.0, content="# repo")

        errs = _run_gate(cdf, repo)
        kinds = {(e.kind, e.path) for e in errs}
        if not any(
            k == "presence-readme" and "src" in p.replace("\\", "/")
            for k, p in kinds
        ):
            failures.append(
                "Case 5 FAIL: folder with files but no README/index did "
                f"NOT trigger presence-readme. Errors: {sorted(kinds)}"
            )

    # --- Case 6: tracks_dir cross-tree dependency ---------------------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_tracks_dir_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        # Set up: src/ has source code; docs/page.md tracks it via
        # frontmatter. Both committed at the same 13h-ago point.
        _commit_at(repo, "src/lib.rs", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(
            repo,
            "docs/page.md",
            age_hours=13.0,
            content=(
                "---\nfacts: []\ntracks: src/\n---\n# page tracks src/\n"
            ),
        )
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")

        # Clean baseline -- no tracks-dir errors expected.
        errs = _run_gate(cdf, repo)
        if any(e.kind == "tracks" for e in errs):
            failures.append(
                "Case 6a FAIL: clean tracks_dir baseline triggered "
                f"tracks-dir error. Errors: {[(e.kind, e.path) for e in errs]}"
            )

        # Drift src/ source so docs/page.md is now older than its tracked
        # content. Pass C is SESSION-WRAP-BOUNDED: it fires only when BOTH
        # (a) a tracked file is newer than the .md AND (b) the current
        # commit STAGES a handoff.
        time.sleep(1.1)
        _commit_at(repo, "src/lib.rs", age_hours=0.0, content="// v2")
        _commit_at(repo, "src/README.md", age_hours=0.0, content="# src v2")

        # Case 6b: code drift, NO handoff anywhere, nothing staged ->
        # mid-session commit -> cascade MUST NOT fire.
        errs = _run_gate(cdf, repo)
        if any(e.kind == "tracks" and "page.md" in e.path for e in errs):
            failures.append(
                "Case 6b FAIL: mid-session code drift (no handoff) DID "
                "trigger tracks-dir. Pass C must stay silent when no "
                "handoff is staged. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

        # Commit a handoff INTO HISTORY (not staged). Pre-fix the cascade
        # keyed off the newest handoff file's mtime, so this state fired on
        # EVERY subsequent commit.
        _commit_at(
            repo,
            ".claude/handoffs/handoff_canary.md",
            age_hours=0.0,
            content="# handoff",
        )

        # Case 6c: a handoff exists in history but is NOT staged in this
        # commit -> cascade MUST NOT fire. This is the regression guard
        # for the session-long mis-fire bug.
        errs = _run_gate(cdf, repo)
        if any(e.kind == "tracks" and "page.md" in e.path for e in errs):
            failures.append(
                "Case 6c FAIL: a handoff in history (not staged in this "
                "commit) re-triggered tracks-dir. Pass C must key off the "
                "STAGED set (handoff_in_staged_commit), not the newest "
                "handoff mtime. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

        # Case 6d: stage a handoff (git add, no commit) -> this IS the
        # session-wrap commit -> cascade MUST fire on the stale page.
        _stage(
            repo,
            ".claude/handoffs/handoff_canary2.md",
            content="# handoff 2",
        )
        errs = _run_gate(cdf, repo)
        if not any(
            e.kind == "tracks" and "page.md" in e.path for e in errs
        ):
            failures.append(
                "Case 6d FAIL: a staged handoff (the session-wrap "
                "commit) + drifted tracked code did NOT trigger "
                "tracks-dir on the tracking page. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 6E: tracks (FILE entry) fires on the tracked file -------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_tracks_file_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "src/schema.ts", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(
            repo, "docs/db.md", age_hours=13.0,
            content="---\ntracks: src/schema.ts\n---\n# tracks schema.ts\n",
        )
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")

        errs = _run_gate(cdf, repo)
        if any(e.kind == "tracks" for e in errs):
            failures.append(
                f"Case 6E-clean FAIL: clean file-track fired. {[(e.kind, e.path) for e in errs]}"
            )

        time.sleep(1.1)
        _commit_at(repo, "src/schema.ts", age_hours=0.0, content="// v2")
        _stage(repo, ".claude/handoffs/handoff_e.md", content="# h")
        errs = _run_gate(cdf, repo)
        if not any(e.kind == "tracks" and "db.md" in e.path for e in errs):
            failures.append(
                "Case 6E FAIL: tracked-FILE drift + staged handoff did NOT fire. "
                f"{[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 6G: file granularity (untracked sibling must NOT fire) --
    with tempfile.TemporaryDirectory(prefix="cdf_canary_tracks_gran_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "src/schema.ts", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/queue.ts", age_hours=13.0, content="// q1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(
            repo, "docs/db.md", age_hours=13.0,
            content="---\ntracks: src/schema.ts\n---\n# tracks schema.ts\n",
        )
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")

        time.sleep(1.1)
        _commit_at(repo, "src/queue.ts", age_hours=0.0, content="// q2")  # UNTRACKED sibling
        _stage(repo, ".claude/handoffs/handoff_g.md", content="# h")
        errs = _run_gate(cdf, repo)
        if any(e.kind == "tracks" and "db.md" in e.path for e in errs):
            failures.append(
                "Case 6G FAIL: untracked sibling drift fired tracks. Granularity "
                f"broken. {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 6H: missing tracked path -> no fire, no crash ----------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_tracks_missing_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(
            repo, "docs/db.md", age_hours=13.0,
            content="---\ntracks: src/nope.ts\n---\n# tracks a missing file\n",
        )
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _stage(repo, ".claude/handoffs/handoff_m.md", content="# h")
        errs = _run_gate(cdf, repo)  # must not raise
        if any(e.kind == "tracks" and "db.md" in e.path for e in errs):
            failures.append(
                "Case 6H FAIL: a doc tracking a MISSING file fired tracks. "
                f"{[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 7: Pass D -- orphan .md flagged --------------------------
    # An authored .md under docs/ with NO frontmatter contract (no
    # tracks_dir, no frozen_at) and NOT in the exempt set should fire
    # the `orphan-md` error kind.
    with tempfile.TemporaryDirectory(prefix="cdf_canary_orphan_md_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        # Orphan: in docs/, named neither index.md nor under an exempt
        # prefix, with empty/missing frontmatter.
        _commit_at(
            repo, "docs/orphan.md", age_hours=13.0,
            content="# Orphan page with no contract\n\nBody.\n",
        )

        errs = _run_gate(cdf, repo)
        if not any(
            e.kind == "orphan-md" and "orphan.md" in e.path for e in errs
        ):
            failures.append(
                "Case 7 FAIL: orphan .md (no tracks_dir, no frozen_at, "
                "not in exempt set) did NOT trigger Pass D 'orphan-md'. "
                "This is the orphan-content gap -- a page with no "
                "maintenance contract gets stale silently because "
                "nothing forces it to be updated. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 8: Pass D -- page with tracks_dir passes ----------------
    # Same orphan structure but with a tracks_dir frontmatter -- Pass D
    # must NOT flag it (the page declared its cascade contract).
    with tempfile.TemporaryDirectory(prefix="cdf_canary_orphan_passes_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "src/lib.rs", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(
            repo, "docs/page.md", age_hours=13.0,
            content=(
                "---\nfacts: []\ntracks: src/\n---\n"
                "# page tracks src/\n"
            ),
        )

        errs = _run_gate(cdf, repo)
        if any(e.kind == "orphan-md" for e in errs):
            failures.append(
                "Case 8 FAIL: page with tracks_dir frontmatter triggered "
                "Pass D 'orphan-md'. Pages with a declared maintenance "
                "contract are NOT orphans. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 8B: Pass D rejects the removed tracks_dir: key ----------
    with tempfile.TemporaryDirectory(prefix="cdf_canary_deprecated_key_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "src/lib.rs", age_hours=13.0, content="// v1")
        _commit_at(repo, "src/README.md", age_hours=13.0, content="# src")
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(
            repo, "docs/old.md", age_hours=13.0,
            content="---\ntracks_dir: src/\n---\n# uses the removed key\n",
        )
        errs = _run_gate(cdf, repo)
        if not any(
            e.kind == "deprecated-tracks-key" and "old.md" in e.path for e in errs
        ):
            failures.append(
                "Case 8B FAIL: a doc using the removed tracks_dir: key was NOT "
                f"rejected with deprecated-tracks-key. {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 9: Pass D -- index.md is exempt -------------------------
    # Section-index pages are nav, not content -- they should NOT be
    # required to declare tracks_dir/frozen_at.
    with tempfile.TemporaryDirectory(prefix="cdf_canary_index_exempt_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        # Bare index.md with no frontmatter -- expected to pass.
        _commit_at(
            repo, "docs/section/index.md", age_hours=13.0,
            content="# Section nav\n\n- [page1](page1.md)\n",
        )
        # The page1 it links to has frontmatter so it doesn't fire Pass D.
        _commit_at(
            repo, "docs/section/page1.md", age_hours=13.0,
            content="---\nfrozen_at: 2026-01-01\n---\n# page1\n",
        )

        errs = _run_gate(cdf, repo)
        if any(e.kind == "orphan-md" for e in errs):
            failures.append(
                "Case 9 FAIL: bare index.md triggered Pass D 'orphan-md'. "
                "Section-index pages are exempt by name -- they're nav, "
                "not content. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

    # --- Case 10: Pass D -- derived_from: exempts (PRESENTATION pages) -
    # Pages with `derived_from: [src1, src2]` are PRESENTATION pages
    # regenerated from the listed sources, not hand-maintained.
    # They satisfy Pass D's contract requirement via derived_from: alone.
    with tempfile.TemporaryDirectory(prefix="cdf_canary_derived_from_") as td:
        repo = Path(td).resolve()
        _git_init(repo)
        _commit_at(repo, "README.md", age_hours=13.0, content="# repo")
        _commit_at(repo, "docs/README.md", age_hours=13.0, content="# docs")
        _commit_at(
            repo, "docs/source.md", age_hours=13.0,
            content="---\ntracks: src/\n---\n# source page\n",
        )
        # Presentation page: declares derived_from + nothing else. Should
        # NOT trigger orphan-md.
        _commit_at(
            repo, "docs/presentation.md", age_hours=13.0,
            content=(
                "---\nderived_from:\n  - docs/source.md\n  - README.md\n---\n"
                "# regenerated\n"
            ),
        )

        errs = _run_gate(cdf, repo)
        if any(
            e.kind == "orphan-md" and "presentation.md" in e.path
            for e in errs
        ):
            failures.append(
                "Case 10 FAIL: page with `derived_from:` frontmatter "
                "triggered Pass D 'orphan-md'. PRESENTATION pages declare "
                "their contract via derived_from: and must NOT be flagged "
                "as orphans. "
                f"Errors: {[(e.kind, e.path) for e in errs]}"
            )

    if failures:
        print(
            f"[test_check_doc_freshness] FAIL -- {len(failures)} case(s):",
            file=sys.stderr,
        )
        # SERIAL_OK_LOOP: prints up to ~10 case-failure messages; fires only on regression
        for f in failures:
            # SERIAL_OK_STDOUT: ephemeral pre-commit canary failure report; fires only on regression
            print(f"  {f}", file=sys.stderr)
        return 1

    print(
        "[test_check_doc_freshness] OK -- sibling rule absent (no presence-md / "
        "mtime-md fires); gate detects mtime-readme cascade, presence-readme "
        "missing, cross-tree tracks drift (file + dir entries), the "
        "deprecated-key rejection, AND Pass D orphan-md (with index.md + "
        "tracks/frozen_at/derived_from exemptions); ignores clean baselines."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
