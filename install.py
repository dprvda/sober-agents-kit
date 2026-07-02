#!/usr/bin/env python3
# REASON: cross-platform installer for the dprvda-kit — copies the template payload into a target
# repo (or promotes it in place), namespaces it under .claude/<kit>, substitutes the project name,
# wires optional language packs, strips opt-out modules, sizes the SessionStart injector to the
# target's corpus, and installs pre-commit. One Python implementation serves both the PowerShell and
# bash wrappers instead of duplicating fragile JSON-editing logic in two shells.
"""dprvda-kit installer.

Usage:
  python install.py --target /path/to/repo [options]   # install into an existing repo
  python install.py --here                              # promote template/ into the current dir
                                                         # (for the GitHub-template flow)

Options:
  --target PATH        target repo (default: required unless --here)
  --here               install into the current working directory
  --project-name NAME  value for __PROJECT_NAME__ (default: target folder name)
  --project-owner OWN  value for __PROJECT_OWNER__ in .mcp.json (default: blank)
  --kit-name NAME      namespace dir under .claude/ (default: dprvda-kit)
  --tools LIST         comma list of AI tools this repo is used with:
                       claude,codex,openclaw,hermes (default: claude).
                       codex/openclaw -> skills are mirrored into .agents/skills/ (the
                       agentskills.io location both read); openclaw/hermes -> the copy command
                       for their user-level skills dir is printed (never written to $HOME);
                       without claude -> the Claude-only live layer (settings.json, hooks/,
                       session injector) is stripped. The git-level gates install for every tool.
  --rust               also install the Rust pack (cargo-audit, cargo-vet, binary-secrets)
  --python             also install the Python pack (ruff lint)
  --no-ai-judge        do NOT install the AI code-review judge (critic_llm*, launch hook)
  --no-mcp             do NOT install the MCP config + serena/github nudges
  --no-precommit       skip `pre-commit install`
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parent
TEMPLATE = KIT_ROOT / "template"
PACKS = KIT_ROOT / "packs"

TEXT_EXTS = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".env", ".example", ".gitignore"}
# Files that must NOT clobber a project's existing copy — written side-by-side instead.
KEEP_BOTH = {"CLAUDE.md", ".pre-commit-config.yaml"}
APPEND_IF_EXISTS = {".gitignore"}


def log(msg: str) -> None:
    print(f"[install] {msg}")


def warn(msg: str) -> None:
    print(f"[install] WARNING: {msg}", file=sys.stderr)


def is_text(p: Path) -> bool:
    return p.suffix in TEXT_EXTS or p.name in (".gitignore", ".env.example")


def copy_payload(src: Path, dst: Path) -> list[str]:
    """Copy src tree into dst with safe rules. Returns list of notes."""
    notes: list[str] = []
    for item in sorted(src.rglob("*")):
        rel = item.relative_to(src)
        out = dst / rel
        if item.is_dir():
            out.mkdir(parents=True, exist_ok=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            if item.name in APPEND_IF_EXISTS:
                existing = out.read_text(encoding="utf-8")
                add = item.read_text(encoding="utf-8")
                if "dprvda-kit" not in existing:
                    out.write_text(existing.rstrip() + "\n\n# --- dprvda-kit ---\n" + add, encoding="utf-8")
                    notes.append(f"appended kit rules to existing {rel}")
                continue
            if item.name in KEEP_BOTH:
                side = out.with_name(out.stem + ".dprvda-kit" + out.suffix)
                shutil.copy2(item, side)
                notes.append(f"{rel} already exists — wrote {side.name} alongside; MERGE MANUALLY")
                continue
            bak = out.with_name(out.name + ".kit-bak")
            shutil.copy2(out, bak)
            notes.append(f"backed up existing {rel} -> {bak.name}")
        shutil.copy2(item, out)
    return notes


def substitute(dst: Path, project_name: str, project_owner: str) -> None:
    for p in dst.rglob("*"):
        if p.is_file() and is_text(p) and ".kit-bak" not in p.name:
            try:
                s = p.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            o = s
            s = s.replace("__PROJECT_NAME__", project_name)
            s = s.replace("__PROJECT_OWNER__", project_owner)
            if s != o:
                p.write_text(s, encoding="utf-8")


def rename_kit(dst: Path, kit_name: str) -> None:
    if kit_name == "dprvda-kit":
        return
    src = dst / ".claude" / "dprvda-kit"
    if src.exists():
        src.rename(dst / ".claude" / kit_name)
    # rewrite references in the wiring files
    for rel in (".claude/settings.json", ".pre-commit-config.yaml",
                f".claude/{kit_name}/hooks/check-script-launch.py"):
        f = dst / rel
        if f.exists():
            f.write_text(f.read_text(encoding="utf-8").replace("dprvda-kit", kit_name), encoding="utf-8")


def install_pack(dst: Path, kit_name: str, pack: str, roster_entries: list[tuple[str, str]]) -> None:
    pack_gates = PACKS / pack / "gates"
    if not pack_gates.exists():
        warn(f"pack '{pack}' not found, skipping")
        return
    gates_dst = dst / ".claude" / kit_name / "gates"
    for g in pack_gates.glob("*.py"):
        shutil.copy2(g, gates_dst / g.name)
    # append roster entries to run_gates_parallel.py PHASE2_GATES
    disp = gates_dst / "run_gates_parallel.py"
    s = disp.read_text(encoding="utf-8")
    anchor = "PHASE2_GATES = ["
    idx = s.index(anchor) + len(anchor)
    add = "".join(f'\n    ("{n}", "{fn}", True),' for n, fn in roster_entries
                  if f'"{fn}"' not in s)
    if add:
        s = s[:idx] + add + s[idx:]
        disp.write_text(s, encoding="utf-8")
    log(f"installed {pack} pack")


def strip_ai_judge(dst: Path, kit_name: str) -> None:
    # Remove the per-file AI review judge + the launch-time hook. KEEP
    # critic_llm_commit.py — its deterministic Conventional-Commits format check
    # needs no key, and its optional LLM cross-check already soft-passes without one.
    # The dispatcher existence-filters critic_llm, so no roster edit is needed.
    base = dst / ".claude" / kit_name
    (base / "gates" / "critic_llm.py").unlink(missing_ok=True)
    (base / "gates" / "prompts" / "critic_llm.md").unlink(missing_ok=True)
    (base / "hooks" / "check-script-launch.py").unlink(missing_ok=True)
    _strip_settings_hook(dst, "check-script-launch.py")
    log("AI per-file judge omitted (--no-ai-judge); commit-msg format validation kept")


def strip_mcp(dst: Path, kit_name: str) -> None:
    (dst / ".mcp.json").unlink(missing_ok=True)
    for h in ("nudge-to-serena.py", "nudge-to-github-mcp.py"):
        (dst / ".claude" / kit_name / "hooks" / h).unlink(missing_ok=True)
    _strip_settings_hook(dst, "nudge-to-serena.py")
    _strip_settings_hook(dst, "nudge-to-github-mcp.py")
    log("MCP config omitted (--no-mcp)")


def _load_settings(dst: Path):
    import json
    f = dst / ".claude" / "settings.json"
    return f, json.loads(f.read_text(encoding="utf-8"))


def _save_settings(f: Path, data) -> None:
    import json
    f.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _strip_settings_hook(dst: Path, script_name: str) -> None:
    f, data = _load_settings(dst)
    for event in data.get("hooks", {}).values():
        for matcher in event:
            matcher["hooks"] = [h for h in matcher.get("hooks", []) if script_name not in h.get("command", "")]
    _save_settings(f, data)


def size_sessionstart(dst: Path, kit_name: str) -> None:
    inj = dst / ".claude" / kit_name / "inject_context_docs.py"
    if not inj.exists():
        return
    try:
        out = subprocess.run([sys.executable, str(inj), "--count"], cwd=dst,
                             capture_output=True, text=True, timeout=30)
        n = int(out.stdout.strip())
    except (OSError, subprocess.SubprocessError, ValueError):
        warn("could not size SessionStart; leaving default")
        return
    n = max(1, min(n, 200))
    f, data = _load_settings(dst)
    cmd = f'python "$CLAUDE_PROJECT_DIR/.claude/{kit_name}/inject_context_docs.py"'
    entries = [{"type": "command", "command": f"{cmd} --chunk {i}", "timeout": 10} for i in range(1, n + 1)]
    for ss in data.get("hooks", {}).get("SessionStart", []):
        ss["hooks"] = entries
    _save_settings(f, data)
    log(f"sized SessionStart to {n} chunk(s)")


def mirror_skills_for_agents(dst: Path) -> None:
    # Codex + OpenClaw read repo-level skills from .agents/skills/ (the agentskills.io
    # convention); Claude Code reads .claude/skills/. Mirror so one skill set serves both.
    src = dst / ".claude" / "skills"
    out = dst / ".agents" / "skills"
    if not src.exists():
        return
    for item in src.rglob("*"):
        rel = item.relative_to(src)
        o = out / rel
        if item.is_dir():
            o.mkdir(parents=True, exist_ok=True)
        else:
            o.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, o)
    log("mirrored skills into .agents/skills/ (Codex / OpenClaw)")


def strip_claude_live_layer(dst: Path, kit_name: str) -> None:
    # No Claude Code in the tool list: the live layer (settings hooks, session injector,
    # in-session guards) has nothing to run it. The git-level gates + AGENTS.md + skills stay.
    base = dst / ".claude"
    (base / "settings.json").unlink(missing_ok=True)
    (base / "settings.local.json.example").unlink(missing_ok=True)
    (base / kit_name / "inject_context_docs.py").unlink(missing_ok=True)
    hooks = base / kit_name / "hooks"
    if hooks.exists():
        shutil.rmtree(hooks)
    log("Claude Code live layer omitted (no 'claude' in --tools); git-level gates kept")


def run_precommit(dst: Path) -> None:
    if not shutil.which("pre-commit"):
        log("pre-commit not found; install with: pip install pre-commit")
        return
    for args in (["pre-commit", "install"],
                 ["pre-commit", "install", "--hook-type", "commit-msg", "--hook-type", "post-commit"]):
        subprocess.run(args, cwd=dst, check=False)
    log("pre-commit hooks installed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target")
    ap.add_argument("--here", action="store_true")
    ap.add_argument("--project-name")
    ap.add_argument("--project-owner", default="")
    ap.add_argument("--kit-name", default="dprvda-kit")
    ap.add_argument("--tools", default="claude")
    ap.add_argument("--rust", action="store_true")
    ap.add_argument("--python", action="store_true")
    ap.add_argument("--no-ai-judge", action="store_true")
    ap.add_argument("--no-mcp", action="store_true")
    ap.add_argument("--no-precommit", action="store_true")
    args = ap.parse_args()

    if args.here:
        dst = Path.cwd()
    elif args.target:
        dst = Path(args.target).resolve()
    else:
        ap.error("one of --target or --here is required")
        return 2
    if not dst.exists():
        ap.error(f"target does not exist: {dst}")
    project_name = args.project_name or dst.name
    tools = {t.strip().lower() for t in args.tools.split(",") if t.strip()}
    known = {"claude", "codex", "openclaw", "hermes", "cursor"}
    for t in tools - known:
        warn(f"unknown tool '{t}' in --tools (known: {', '.join(sorted(known))}); "
             "the git-level gates + AGENTS.md cover it anyway")

    log(f"installing dprvda-kit into {dst} (tools: {', '.join(sorted(tools))})")
    notes = copy_payload(TEMPLATE, dst)

    if args.no_ai_judge:
        strip_ai_judge(dst, "dprvda-kit")
    if args.no_mcp:
        strip_mcp(dst, "dprvda-kit")
    if args.rust:
        install_pack(dst, "dprvda-kit", "rust",
                     [("check_cargo_audit", "check_cargo_audit.py"), ("check_cargo_vet", "check_cargo_vet.py")])
    if args.python:
        install_pack(dst, "dprvda-kit", "python", [("check_python_lint", "check_python_lint.py")])

    rename_kit(dst, args.kit_name)
    substitute(dst, project_name, args.project_owner)
    if tools & {"codex", "openclaw"}:
        mirror_skills_for_agents(dst)
    if "claude" in tools:
        size_sessionstart(dst, args.kit_name)
    else:
        strip_claude_live_layer(dst, args.kit_name)
    if not args.no_precommit:
        run_precommit(dst)

    print()
    log("done.")
    for n in notes:
        log(f"  note: {n}")
    print()
    print("Next steps:")
    print(f"  1. cd {dst}")
    print("  2. Fill in the <!-- FILL IN --> sections of AGENTS.md (the one rules file every tool reads).")
    print("  3. (AI judge) put your key in .env:  LLM_JUDGE_API_KEY=sk-...   (blank = judge soft-passes)")
    if "claude" in tools:
        print("  4. Open the repo in Claude Code:  claude")
    if "codex" in tools:
        print("  *  Codex reads AGENTS.md natively; skills are in .agents/skills/ (invoke via /skills).")
    if "openclaw" in tools:
        print("  *  OpenClaw: skills are project-level in .agents/skills/; for the user-level dir run:")
        print(f"     cp -r {(dst / '.agents' / 'skills').as_posix()}/* ~/.openclaw/skills/")
    if "hermes" in tools:
        print("  *  Hermes reads AGENTS.md/CLAUDE.md; install skills user-level:")
        print(f"     cp -r {(dst / '.claude' / 'skills').as_posix()}/* ~/.hermes/skills/")
    print("  *  Make a test commit to see the gates run (they protect EVERY tool, git-level).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
