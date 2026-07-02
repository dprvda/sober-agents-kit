#!/usr/bin/env python3
# REASON: tool-neutral force-push/branch-delete blocker — the Claude-only PreToolUse hook
# (block-dangerous-git.py) cannot protect Codex/OpenClaw/Hermes sessions, so the same #1
# protection is enforced one level lower as a git pre-push hook: it fires for EVERY tool and
# every human, because `git push` is the one door they all walk through. No existing gate
# covers the push stage (the commit gates run at commit time).
"""pre-push gate: block history rewrites and remote branch deletions.

git invokes pre-push with lines on stdin:  <local_ref> <local_sha> <remote_ref> <remote_sha>
- remote_sha = all zeros  -> new branch, allow.
- local_sha  = all zeros  -> DELETE of a remote branch, block.
- remote_sha not an ancestor of local_sha -> non-fast-forward (a force push), block.

Escape hatch (deliberate, audited): set AGENT_KIT_ALLOW_FORCE_PUSH=1 for one command.
A human can also push from a clone without the hook. An agent cannot quietly rewrite history.
"""
from __future__ import annotations

import os
import subprocess
import sys

ZERO = "0" * 40


def is_ancestor(ancestor: str, descendant: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, descendant],
                       capture_output=True)
    return r.returncode == 0


def main() -> int:
    if os.environ.get("AGENT_KIT_ALLOW_FORCE_PUSH") == "1":
        print("[check_force_push] AGENT_KIT_ALLOW_FORCE_PUSH=1 — allowing this push", file=sys.stderr)
        return 0
    problems: list[str] = []
    for line in sys.stdin:
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if remote_sha == ZERO:
            continue  # new remote branch
        if local_sha == ZERO:
            problems.append(f"DELETE of remote branch {remote_ref}")
            continue
        if not is_ancestor(remote_sha, local_sha):
            # The remote tip is not contained in what we push: history rewrite.
            problems.append(f"NON-FAST-FORWARD (force) push to {remote_ref}")
    if problems:
        print("[check_force_push] BLOCKED:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        print("  History rewrites and remote deletions are blocked for every tool.", file=sys.stderr)
        print("  If this is deliberate and reviewed: AGENT_KIT_ALLOW_FORCE_PUSH=1 git push ...", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
