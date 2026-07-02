#!/usr/bin/env python3
# REASON: cross-platform installer for the agent-kit — copies the template payload into a target
# repo (or promotes it in place), namespaces it under a root-level .<kit> dir, substitutes the project name,
# wires optional language packs, strips opt-out modules, sizes the SessionStart injector to the
# target's corpus, and installs pre-commit. One Python implementation serves both the PowerShell and
# bash wrappers instead of duplicating fragile JSON-editing logic in two shells.
"""agent-kit installer.

Usage:
  python install.py --target /path/to/repo [options]   # install into an existing repo
  python install.py --here                              # promote template/ into the current dir
                                                         # (for the GitHub-template flow)

Options:
  --target PATH        target repo (default: required unless --here)
  --here               install into the current working directory
  --project-name NAME  value for __PROJECT_NAME__ (default: target folder name)
  --project-owner OWN  value for __PROJECT_OWNER__ in .mcp.json (default: blank)
  --kit-name NAME      the root-level kit dir name, dot-prefixed (default: agent-kit -> .agent-kit/)
  --tools LIST         comma list of AI tools this repo is used with:
                       claude,codex,openclaw,hermes (default: claude).
                       Skills are canonical in .agents/skills/ (agentskills.io — Codex + OpenClaw
                       read it natively); with claude they are mirrored into .claude/skills/.
                       Without claude the Claude adapter (settings.json, .agent-kit/adapters/claude/) is
                       stripped. The git-level gates + the session module install for every tool.
  --install-user-skills  also copy the skills into the user-level dirs of the chosen tools
                       (~/.openclaw/skills, ~/.hermes/skills) instead of only printing the command
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
                if "agent-kit" not in existing:
                    out.write_text(existing.rstrip() + "\n\n# --- agent-kit ---\n" + add, encoding="utf-8")
                    notes.append(f"appended kit rules to existing {rel}")
                continue
            if item.name in KEEP_BOTH:
                side = out.with_name(out.stem + ".agent-kit" + out.suffix)
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


def kit_dir(dst: Path, kit_name: str) -> Path:
    # The kit machinery lives at the repo ROOT (tool-neutral home), dot-prefixed:
    # .agent-kit/ by default, .<kit-name>/ after a rename.
    return dst / f".{kit_name}"


def rename_kit(dst: Path, kit_name: str) -> None:
    if kit_name == "agent-kit":
        return
    src = dst / ".agent-kit"
    if src.exists():
        src.rename(kit_dir(dst, kit_name))
    # rewrite references in the wiring files
    for rel in (".claude/settings.json", ".pre-commit-config.yaml",
                f".{kit_name}/adapters/claude/hooks/check-script-launch.py"):
        f = dst / rel
        if f.exists():
            f.write_text(f.read_text(encoding="utf-8").replace("agent-kit", kit_name), encoding="utf-8")


def install_pack(dst: Path, kit_name: str, pack: str, roster_entries: list[tuple[str, str]]) -> None:
    pack_gates = PACKS / pack / "gates"
    if not pack_gates.exists():
        warn(f"pack '{pack}' not found, skipping")
        return
    gates_dst = kit_dir(dst, kit_name) / "gates"
    for g in pack_gates.glob("*.py"):
        shutil.copy2(g, gates_dst / g.name)
    # pack-level config files (e.g. python's ruff.toml) land at the repo root, never clobbering
    for cfg in (PACKS / pack).glob("*"):
        if cfg.is_file() and cfg.name != "README.md" and not (dst / cfg.name).exists():
            shutil.copy2(cfg, dst / cfg.name)
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
    base = kit_dir(dst, kit_name)
    (base / "gates" / "critic_llm.py").unlink(missing_ok=True)
    (base / "gates" / "prompts" / "critic_llm.md").unlink(missing_ok=True)
    (base / "adapters" / "claude" / "hooks" / "check-script-launch.py").unlink(missing_ok=True)
    _strip_settings_hook(dst, "check-script-launch.py")
    log("AI per-file judge omitted (--no-ai-judge); commit-msg format validation kept")


def strip_mcp(dst: Path, kit_name: str) -> None:
    (dst / ".mcp.json").unlink(missing_ok=True)
    for h in ("nudge-to-serena.py", "nudge-to-github-mcp.py"):
        (kit_dir(dst, kit_name) / "adapters" / "claude" / "hooks" / h).unlink(missing_ok=True)
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
    inj = kit_dir(dst, kit_name) / "session" / "inject_context_docs.py"
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
    cmd = f'python "$CLAUDE_PROJECT_DIR/.{kit_name}/session/inject_context_docs.py"'
    entries = [{"type": "command", "command": f"{cmd} --chunk {i}", "timeout": 10} for i in range(1, n + 1)]
    for ss in data.get("hooks", {}).get("SessionStart", []):
        ss["hooks"] = entries
    _save_settings(f, data)
    log(f"sized SessionStart to {n} chunk(s)")


def mirror_skills_for_claude(dst: Path) -> None:
    # The canonical skills home is the cross-tool .agents/skills/ (agentskills.io — Codex +
    # OpenClaw read it natively). Claude Code reads .claude/skills/, so mirror for it.
    src = dst / ".agents" / "skills"
    out = dst / ".claude" / "skills"
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
    log("mirrored skills into .claude/skills/ (Claude Code)")


def strip_claude_live_layer(dst: Path, kit_name: str) -> None:
    # No Claude Code in the tool list: the live layer (settings hooks, session injector,
    # in-session guards) has nothing to run it. The git-level gates + AGENTS.md + skills stay.
    claude_dir = dst / ".claude"
    if claude_dir.exists():
        shutil.rmtree(claude_dir)
    adapter = kit_dir(dst, kit_name) / "adapters" / "claude"
    if adapter.exists():
        shutil.rmtree(adapter)
    (dst / ".mcp.json").unlink(missing_ok=True)  # Claude's MCP config file — nothing reads it
    log("Claude Code adapter omitted (no 'claude' in --tools); git-level gates + session kept")


def resolve_agents_md(dst: Path, tools: set[str]) -> None:
    # AGENTS.md ships with fenced conditional blocks; they are resolved ONCE here, per the
    # confirmed tool set, so the standing file that every session re-reads carries ZERO
    # "if your tool is X" prose. The conditionals live in the interview + this function.
    import re
    agents = dst / "AGENTS.md"
    if not agents.exists():
        return
    s = agents.read_text(encoding="utf-8")
    def cut(block: str, text: str) -> str:
        return re.sub(rf"<!-- {block}-start -->.*?<!-- {block}-end -->\n?", "", text, flags=re.S)
    def unfence(block: str, text: str) -> str:
        return text.replace(f"<!-- {block}-start -->\n", "").replace(f"<!-- {block}-end -->\n", "")
    if "claude" not in tools:
        s = cut("claude-adapter", s)          # nothing reads the adapter README
    else:
        s = unfence("claude-adapter", s)
    if tools == {"claude"}:
        s = cut("non-claude-session", s)      # session spine auto-injects; the instruction is waste
    else:
        s = unfence("non-claude-session", s)
    agents.write_text(s, encoding="utf-8")


def install_user_skills(dst: Path, tools: set[str]) -> None:
    # Opt-in only (--install-user-skills): writes into the user's HOME for tools whose skill
    # dir is user-level. Never silent — each copy is logged.
    src = dst / ".agents" / "skills"
    if not src.exists():
        return
    targets = []
    if "openclaw" in tools:
        targets.append(Path.home() / ".openclaw" / "skills")
    if "hermes" in tools:
        targets.append(Path.home() / ".hermes" / "skills")
    for tgt in targets:
        for item in src.rglob("*"):
            rel = item.relative_to(src)
            o = tgt / rel
            if item.is_dir():
                o.mkdir(parents=True, exist_ok=True)
            else:
                o.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, o)
        log(f"skills copied to {tgt}")


def run_precommit(dst: Path) -> None:
    if not shutil.which("pre-commit"):
        log("pre-commit not found; install with: pip install pre-commit")
        return
    for args in (["pre-commit", "install"],
                 ["pre-commit", "install", "--hook-type", "commit-msg", "--hook-type", "post-commit", "--hook-type", "pre-push"]):
        subprocess.run(args, cwd=dst, check=False)
    log("pre-commit hooks installed")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target")
    ap.add_argument("--here", action="store_true")
    ap.add_argument("--project-name")
    ap.add_argument("--project-owner", default="")
    ap.add_argument("--kit-name", default="agent-kit")
    ap.add_argument("--tools", default="claude")
    ap.add_argument("--rust", action="store_true")
    ap.add_argument("--python", action="store_true")
    ap.add_argument("--no-ai-judge", action="store_true")
    ap.add_argument("--no-mcp", action="store_true")
    ap.add_argument("--no-precommit", action="store_true")
    ap.add_argument("--install-user-skills", action="store_true")
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

    log(f"installing agent-kit into {dst} (tools: {', '.join(sorted(tools))})")
    notes = copy_payload(TEMPLATE, dst)

    if args.no_ai_judge:
        strip_ai_judge(dst, "agent-kit")
    if args.no_mcp:
        strip_mcp(dst, "agent-kit")
    if args.rust:
        install_pack(dst, "agent-kit", "rust",
                     [("check_cargo_audit", "check_cargo_audit.py"), ("check_cargo_vet", "check_cargo_vet.py")])
    if args.python:
        install_pack(dst, "agent-kit", "python", [("check_python_lint", "check_python_lint.py")])

    rename_kit(dst, args.kit_name)
    substitute(dst, project_name, args.project_owner)
    if "claude" in tools:
        mirror_skills_for_claude(dst)
        size_sessionstart(dst, args.kit_name)
    else:
        strip_claude_live_layer(dst, args.kit_name)
    if tools == {"claude"}:
        # Claude reads only the .claude/skills mirror — the canonical .agents/ copy would be
        # a dead duplicate in a claude-only repo (issue #11). The tree is a function of --tools.
        agents_dir = dst / ".agents"
        if agents_dir.exists():
            shutil.rmtree(agents_dir)
            log("removed .agents/ (claude-only install; .claude/skills is the live copy)")
    resolve_agents_md(dst, tools)
    if args.install_user_skills:
        install_user_skills(dst, tools)
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
        print("  *  Hermes reads AGENTS.md/CLAUDE.md; skills go user-level (~/.hermes/skills/).")
    print("  *  Make a test commit to see the gates run (they protect EVERY tool, git-level).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
