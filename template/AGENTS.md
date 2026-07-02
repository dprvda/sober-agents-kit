# Project: __PROJECT_NAME__ — RULES ONLY (canonical for ALL agents)

This file is **rules-only** — the ONE canonical instruction file, read natively by Codex / Cursor /
OpenClaw / Hermes / Continue / Aider / any AGENTS.md-aware tool, and imported by Claude Code via the
one-line CLAUDE.md. State / architecture / reference docs live under `docs/`. The kit's
machinery lives under [`.agent-kit/`](.agent-kit/). Keep this file short
(`check_md_size` enforces a budget); link, don't duplicate.
<!-- claude-adapter-start -->
The Claude-Code-specific wiring (live hooks, settings) is specced in
[the Claude adapter README](.agent-kit/adapters/claude/README.md).
<!-- claude-adapter-end -->

<!-- FILL IN: one or two sentences on what this project IS, so a fresh session is oriented. -->

## FIRST ACTION of every session (all tools)

Run `python .agent-kit/session/inject_context_docs.py --all` and read its output BEFORE doing
anything else: it prints the project spine (key docs, the live progress ledger, recent state) so
you never start blind. Claude Code runs this automatically at session start; every other agent
runs it as this file's first instruction.

## Pre-commit gates (enforced on `git commit` — NEVER `--no-verify`)

Dispatcher: `.agent-kit/gates/run_gates_parallel.py` (phase 1 serial → phase 2 parallel).

- `critic_llm` — AI judge over each staged source file. Soft-passes when `LLM_JUDGE_API_KEY` is
  unset. On a real issue it prepends `=== LLM_REVIEW_BLOCK ===` to the file (see protocol below).
- `check_file_reason` — every `.py`/`.sh`/`.rs`/… declares a `# REASON:` header (≥30 chars).
- `check_links` — every `.md` cross-reference resolves.
- `check_doc_freshness` — folder READMEs + `tracks_dir:` cascade + orphan-md contract.
- `check_md_size` — per-doc character budget.
- `check_secrets` — staged text scanned for secret-shaped strings (keys, tokens, private keys).
- `check_force_push` (pre-push stage) — blocks force-pushes and remote branch deletions for
  EVERY tool and every human clone (escape: `AGENT_KIT_ALLOW_FORCE_PUSH=1`, deliberate only).

A hook failure blocks the commit. **Fix the cause — never bypass.**

## `=== LLM_REVIEW_BLOCK ===` protocol (read first when you see one)

The AI judge prepends a comment block to a source file: top marker → `Summary:` → numbered
`L<line> (severity, category): issue -> fix` → end marker. When you see one: (1) read every item,
(2) **fix the code** (deleting the block alone re-triggers it next commit), (3) remove the whole
block (top marker through end), (4) re-stage + re-commit.

## Commit messages — Conventional Commits 1.0 (`commit-msg` gate)

`<type>(<scope>)?!?: <subject ≤99>` → blank → body (WHY; required if >50 LOC) → blank → trailers.

- **types**: `feat | fix | refactor | perf | docs | test | build | ci | chore | revert` (must match the diff).
- **scopes** (EDIT for your project): `core | cli | api | ui | docs | build | ci | deps | meta`.
- **trailers**: `Closes #N`, `Co-Authored-By:`, `BREAKING CHANGE:` (or `!`), `Tag: vX.Y.Z`
  (strict SemVer; bump computed deterministically — any breaking → major, any `feat` → minor,
  any `fix`/`perf`/`refactor` → patch).

## NO bypasses — fix the root cause

- NO `--no-verify` / `--skip-hooks`. Fix what the hook caught.
- NO disabling tests / `assert True` / commented-out assertions.
- NO catching-and-ignoring exceptions (`except: pass`, error-hiding `unwrap_or_default()`).
- NO `TODO` comments deferring required work — do it now or open a tracked issue.
- Visible bug/anomaly → fix it in the CURRENT turn.

## `archive/` — out of context

Files under `archive/` (any depth) are out-of-context. Don't read unless the user references one by
path. Gates skip them. Revive with `git mv archive/<path> <path>`.

## Tempo — deadlines fit dozens of tasks, not one

Time horizons ("by morning", "while I'm away") are DEADLINES, not scopes. Don't pad, don't idle,
quality bar stays full per item. Backlog empty → write a short autopilot-proposal doc and continue
on docs/cleanup. Never auto-pause.

<!-- claude-adapter-start -->
## Live hooks — Claude Code only (`.claude/settings.json` → `.agent-kit/adapters/claude/hooks/`)

When the session runs in Claude Code, these fire in-session (other tools rely on the git-level
gates above, which protect every tool):

- `block-dangerous-git.py` — blocks history-rewrite git ops (force-push, `reset --hard`,
  `clean -f`, `checkout/restore .`, `branch -D`, `filter-branch`). Normal `push` to any branch is fine.
- `check-script-launch.py` — runs the AI judge on a script before Bash launches it; blocks only on
  `severity=block`; fail-open.
- `nudge-to-*` — soft PostToolUse suggestions to use MCP tools (never block).
<!-- claude-adapter-end -->

## Skills (saved procedures — invoke by name in any tool that reads them)

Cross-tool SKILL.md format (agentskills.io). The canonical home is `.agents/skills/` (Codex and
OpenClaw read it natively; Hermes copies from it); Claude Code reads the `.claude/skills/` mirror
made at install.

- `sober-setup` — audit/update this project's kit setup (playbook lives in the kit repo)
- `handoff` — save verified progress notes so the next session continues without re-explaining
- `graphify` — standalone code-graph tool (bundled); one graph query replaces reading ten files
- `systematic-debugging` — find the real cause before fixing; rethink after 3 failed attempts
- `subagent-driven-development` — parallel isolated workers + an independent reviewer per task
- `receiving-code-review` — verify review feedback before acting, never flatter
- `tdd` — test before code · `grill-me` — interrogate a plan before building
- `to-issues` — split a plan into grabbable tickets · `compact-docs` — trim over-budget docs
- `audit-structure` — folder/naming review · `zoom-out` — re-orient after a deep dive
- `caveman` — ultra-short answers mode · `write-a-skill` — teach the AI a new procedure

See each `SKILL.md` for the full procedure.

## Critical project rules

<!-- FILL IN: the handful of domain rules a fresh session MUST know and must not re-litigate.
     e.g. "X is the only valid source for Y", "never do Z in production". Keep to the essentials —
     everything else lives in docs/. Delete this comment once filled. -->
