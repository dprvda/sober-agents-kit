#!/usr/bin/env python3
# REASON: two-phase pre-commit gate dispatcher for the dprvda-kit — runs phase 1 serially
# (code-discipline gates that may mutate the working tree, e.g. the AI judge) then phase 2
# in parallel (read-only doc gates), because phase-2 gates must read post-mutation file
# content and fanning them out concurrently keeps the whole commit hook near ~phase1+slowest.
# Gates whose script is absent are skipped (so optional modules / language packs need no edit
# here) instead of crashing the commit.
"""run_gates_parallel.py — dprvda-kit pre-commit gate dispatcher.

Default roster (all language-agnostic, all blocking):

  Phase 1 — serial, fail-fast (code discipline; may mutate the tree):
    critic_llm        — AI judge per staged source file (soft-passes w/o a key)
    check_file_reason — every script declares a `# REASON:` header

  Phase 2 — parallel (read-only doc + safety discipline):
    check_links       — every .md cross-reference resolves
    check_doc_freshness — folder-README + tracks_dir cascade + orphan-md
    check_md_size     — per-doc character budget
    check_secrets     — staged text scanned for secret-shaped strings

Language packs (Rust, Python, ...) append their gates to this list at install
time. A gate whose script file does not exist is skipped with a notice — so
disabling the AI judge (delete critic_llm.py) or installing without a pack
needs no change here.

Exit: 0 = all blocking gates passed (or skipped); 1 = a blocking gate failed.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

GATES_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]

# (gate_name, script_filename, blocking)
PHASE1_GATES = [
    ("critic_llm",        "critic_llm.py",        True),
    ("check_file_reason", "check_file_reason.py", True),
]
PHASE2_GATES = [
    ("check_links",         "check_links.py",         True),
    ("check_doc_freshness", "check_doc_freshness.py", True),
    ("check_md_size",       "check_md_size.py",       True),
    ("check_secrets",       "check_secrets.py",       True),
]
GATES = PHASE1_GATES + PHASE2_GATES


@dataclass
class GateResult:
    name: str
    blocking: bool
    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float

    @property
    def passed(self) -> bool:
        return True if not self.blocking else self.returncode == 0

    def label(self) -> str:
        return ("PASS" if self.returncode == 0 else "FAIL") if self.blocking else "warn"


def run_gate(name: str, filename: str, blocking: bool) -> GateResult | None:
    script = GATES_DIR / filename
    if not script.exists():
        return None  # optional gate not installed — skip silently
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=REPO_ROOT, capture_output=True, text=True, check=False,
        )
        return GateResult(name, blocking, proc.returncode, proc.stdout, proc.stderr,
                          time.monotonic() - start)
    except (OSError, subprocess.SubprocessError) as e:
        return GateResult(name, blocking, 2, "", f"[run_gates] failed to invoke {name}: {e}",
                          time.monotonic() - start)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", default="", help="comma-separated subset to run")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    wanted = {g.strip() for g in args.gates.split(",") if g.strip()} if args.gates else None
    phase1 = [g for g in PHASE1_GATES if wanted is None or g[0] in wanted]
    phase2 = [g for g in PHASE2_GATES if wanted is None or g[0] in wanted]

    overall_start = time.monotonic()
    results: list[GateResult] = []

    # Phase 1 — serial, fail-fast.
    phase1_failed = False
    for name, fn, blocking in phase1:
        r = run_gate(name, fn, blocking)
        if r is None:
            continue
        results.append(r)
        if r.blocking and r.returncode != 0:
            phase1_failed = True
            break

    # Phase 2 — parallel, skipped if phase 1 already blocked.
    if phase2 and not phase1_failed:
        present = [(n, fn, b) for (n, fn, b) in phase2 if (GATES_DIR / fn).exists()]
        if present:
            with ThreadPoolExecutor(max_workers=len(present)) as pool:
                futs = {pool.submit(run_gate, n, fn, b): n for (n, fn, b) in present}
                for fut in as_completed(futs):
                    r = fut.result()
                    if r is not None:
                        results.append(r)

    overall = time.monotonic() - overall_start
    order = {n: i for i, (n, _, _) in enumerate(GATES)}
    results.sort(key=lambda r: order.get(r.name, 99))

    if args.json:
        print(json.dumps({
            "ok": all(r.passed for r in results),
            "elapsed_s": round(overall, 2),
            "gates": [{"name": r.name, "rc": r.returncode, "passed": r.passed} for r in results],
        }))
        return 0 if all(r.passed for r in results) else 1

    for r in results:
        if r.stdout.strip() or r.stderr.strip():
            print(f"\n=== {r.name} ({r.label()}, {r.elapsed_s:.1f}s) ===", file=sys.stderr)
            if r.stdout:
                sys.stdout.write(r.stdout)
            if r.stderr:
                sys.stderr.write(r.stderr)

    skipped = " (phase 2 skipped — phase 1 blocked)" if phase1_failed else ""
    print(f"\n[run_gates] {len(results)} gates in {overall:.1f}s{skipped}", file=sys.stderr)
    for r in results:
        print(f"  {r.label():4s}  {r.name:22s}  {r.elapsed_s:6.2f}s  rc={r.returncode}", file=sys.stderr)

    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
