#!/usr/bin/env python3
# REASON: New supply-chain advisory gate — exists because no existing
# pre-commit gate covers RustSec advisories against the full
# transitive set Cargo.lock pulls in (`serde_json`, `tokio`, `rustls`,
# and others). Replaces the operator's manual `cargo audit` discipline
# (today: nothing surfaces an advisory before deploy, so a published
# vuln can ship without the operator seeing the ID). Forces a hard
# block on a known-vulnerable Cargo.lock at commit time. Matches the
# `unavailable_pass` pattern — when `cargo audit` itself is not
# installed the gate exits 0 with a stderr warning so a fresh checkout
# doesn't break-by-default; needs review when running on CI (the
# install hint in packs/rust/README.md is the operator's one-time
# install path).
"""
check_cargo_audit — pre-commit RustSec advisory gate.

Runs `cargo audit --json` against the repo's Cargo.lock. Blocks the
commit on any unfixed advisory; passes silently otherwise. When the
`cargo audit` binary is not installed, the gate emits a one-line
stderr warning + exits 0 (unavailable_pass policy — best-effort, not
break-by-default on a fresh checkout). The operator-side install hint
lives in `packs/rust/README.md`.

Exit codes:
- 0 — clean lockfile OR `cargo audit` not installed
- 1 — at least one advisory matched against Cargo.lock
- 2 — internal error (subprocess setup failed)

Usage:
    python scripts/hooks/check_cargo_audit.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    cargo_audit = shutil.which("cargo-audit") or shutil.which("cargo")
    if not cargo_audit or not shutil.which("cargo"):
        print(
            "[check_cargo_audit] cargo not on PATH — skipping (rc=0, fresh-checkout policy). "
            "Install via `cargo install cargo-audit` to enable.",
            file=sys.stderr,
        )
        return 0

    # `cargo audit` is a subcommand; check it's available.
    probe = subprocess.run(
        ["cargo", "audit", "--version"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    if probe.returncode != 0:
        print(
            "[check_cargo_audit] `cargo audit` not installed — skipping "
            "(rc=0, fresh-checkout policy). Run `cargo install cargo-audit`. "
            f"probe stderr: {probe.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return 0

    rc = subprocess.run(
        ["cargo", "audit", "--json"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    # cargo audit returns rc=0 with no advisories, rc=1 with advisories,
    # rc=other on internal error. Parse the JSON either way to surface
    # the advisory IDs clearly.
    try:
        payload = json.loads(rc.stdout) if rc.stdout.strip() else {}
    except json.JSONDecodeError:
        print(
            f"[check_cargo_audit] cargo audit produced non-JSON output (rc={rc.returncode}); "
            f"stderr_tail={rc.stderr[-400:]}",
            file=sys.stderr,
        )
        return 2

    vulns = payload.get("vulnerabilities", {})
    found = vulns.get("found", False)
    count = vulns.get("count", 0)
    if not found:
        # Silent pass — matches the other gates' "all clean = no output" policy.
        return 0

    # Report each advisory.
    advisories = vulns.get("list", [])
    print(
        f"[check_cargo_audit] BLOCK — {count} unfixed RustSec advisor"
        f"{'ies' if count != 1 else 'y'} in Cargo.lock:",
        file=sys.stderr,
    )
    for adv in advisories:
        advisory = adv.get("advisory", {})
        package = adv.get("package", {})
        aid = advisory.get("id", "?")
        title = advisory.get("title", "?")
        url = advisory.get("url", "")
        name = package.get("name", "?")
        version = package.get("version", "?")
        print(
            f"  - {aid}  {name} {version}: {title}\n    {url}",
            file=sys.stderr,
        )
    print(
        "\nFix path: bump the affected crate via `cargo update -p <name>` "
        "or replace via `cargo upgrade`. Re-run the commit once the lockfile "
        "is clean.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
