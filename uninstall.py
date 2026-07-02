#!/usr/bin/env python3
# REASON: conservative uninstaller for the agent-kit — removes the namespaced machinery dir and
# restores *.kit-bak backups, but LISTS shared root files for manual removal rather than deleting
# user-editable files, because a blind delete could remove a CLAUDE.md / .gitignore the user has
# since customized. Safety over completeness.
"""Remove the agent-kit from a target repo (conservative).

Usage:
  python uninstall.py --target /path/to/repo [--kit-name agent-kit]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Root files the installer may have written. Removed only if still byte-identical
# to the template (i.e. the user has not customized them).
ROOT_FILES = ["AGENTS.md", "CLAUDE.md", ".gitmessage", ".mcp.json", ".env.example"]
KIT_ROOT = Path(__file__).resolve().parent
TEMPLATE = KIT_ROOT / "template"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--kit-name", default="agent-kit")
    args = ap.parse_args()
    dst = Path(args.target).resolve()

    kit = dst / f".{args.kit_name}"
    if kit.exists():
        shutil.rmtree(kit)
        print(f"[uninstall] removed {kit}")
    for mirror in (dst / ".claude" / "skills", dst / ".agents" / "skills"):
        # kit-installed skill mirrors; leave any non-kit skill a user added
        for name in ("sober-setup", "handoff", "graphify", "tdd",
                     "grill-me", "to-issues", "compact-docs", "audit-structure",
                     "zoom-out", "caveman", "write-a-skill"):
            d = mirror / name
            if d.exists():
                shutil.rmtree(d)
        if mirror.exists() and not any(mirror.iterdir()):
            mirror.rmdir()

    # restore backups
    for bak in dst.rglob("*.kit-bak"):
        orig = bak.with_name(bak.name[:-len(".kit-bak")])
        shutil.move(str(bak), str(orig))
        print(f"[uninstall] restored {orig.relative_to(dst)} from backup")

    # remove root files only if unmodified vs template
    manual: list[str] = []
    for name in ROOT_FILES:
        f = dst / name
        t = TEMPLATE / name
        if f.exists() and t.exists():
            if f.read_bytes() == t.read_bytes():
                f.unlink()
                print(f"[uninstall] removed unmodified {name}")
            else:
                manual.append(name)

    if shutil.which("pre-commit"):
        subprocess.run(["pre-commit", "uninstall"], cwd=dst, check=False)

    print("\n[uninstall] done.")
    print("[uninstall] NOT removed (customized or shared — review/remove manually if desired):")
    for n in ["CLAUDE.md", ".pre-commit-config.yaml", ".gitignore (kit block)",
              ".claude/settings.json", *manual]:
        print(f"    - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
