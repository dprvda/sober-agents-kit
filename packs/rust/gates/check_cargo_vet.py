#!/usr/bin/env python3
# REASON: New supply-chain trust gate — exists because `check_cargo_audit` covers KNOWN CVEs but not the per-dep "do we trust this code at all" axis. `cargo vet` enforces that every transitive dep is either (a) explicitly audited (locally or via an imported upstream trust set) or (b) explicitly exempted in `supply-chain/config.toml`. This gate fires when a NEW dep gets added to Cargo.lock without an audit or exemption — forward-only contract per the AFK-able exemptions baseline strategy. Matches `check_cargo_audit`'s `unavailable_pass`-style fresh-checkout policy (cargo-vet not installed = stderr warn + rc=0, never break-by-default).
"""
check_cargo_vet — pre-commit supply-chain trust gate.

Runs `cargo vet check` against the workspace's `supply-chain/config.toml`
baseline. Passes silently when the lockfile is fully covered by audits
+ exemptions; blocks the commit when a new dep is uncovered.

Exit codes:
- 0 — clean lockfile OR `cargo vet` not installed
- 1 — at least one new dep needs an audit or exemption
- 2 — internal error (subprocess setup failed)

Operator workflow when blocked:
1. Read the `cargo vet check` output — it names the uncovered dep.
2. Decide trust: import an upstream audit set via
   `cargo vet aggregate`, or accept the dep into the local baseline
   via `cargo vet certify <crate> <version>` (commits to
   `supply-chain/audits.toml`), or temporarily exempt via
   `cargo vet diff <crate>` then add to `supply-chain/config.toml`.
3. Re-stage `supply-chain/*.toml` + re-commit.

Usage:
    python scripts/hooks/check_cargo_vet.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    if not shutil.which("cargo"):
        print(
            "[check_cargo_vet] cargo not on PATH — skipping (rc=0, "
            "fresh-checkout policy).",
            file=sys.stderr,
        )
        return 0

    probe = subprocess.run(
        ["cargo", "vet", "--version"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    if probe.returncode != 0:
        print(
            "[check_cargo_vet] `cargo vet` not installed — skipping "
            "(rc=0, fresh-checkout policy). Install via "
            "`cargo install cargo-vet --locked`. "
            f"probe stderr: {probe.stderr.strip()[:200]}",
            file=sys.stderr,
        )
        return 0

    if not (ROOT / "supply-chain" / "config.toml").exists():
        print(
            "[check_cargo_vet] supply-chain/config.toml missing — run "
            "`cargo vet init` once to generate the baseline.",
            file=sys.stderr,
        )
        return 1

    rc = subprocess.run(
        ["cargo", "vet", "check"],
        capture_output=True, text=True, cwd=ROOT, check=False,
    )
    if rc.returncode == 0:
        # Silent pass — matches the other gates' "all clean = no output" policy.
        return 0

    print(
        f"[check_cargo_vet] BLOCK — cargo vet check failed (rc={rc.returncode}). "
        "A new transitive dep landed in Cargo.lock without an audit or exemption.\n"
        "Fix path: run `cargo vet suggest` for the per-dep next-action; for a fresh "
        "exemption baseline run `cargo vet regenerate exemptions`. Re-stage "
        "`supply-chain/*.toml` after the fix.",
        file=sys.stderr,
    )
    if rc.stdout.strip():
        print(rc.stdout, file=sys.stderr)
    if rc.stderr.strip():
        print(rc.stderr, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
