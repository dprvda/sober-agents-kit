# Project: __PROJECT_NAME__ — RULES ONLY

This file is **rules-only** and loaded every session. State / architecture / reference docs live
under `docs/`. The full Claude Code setup spec is in [`README-CLAUDE.md`](README-CLAUDE.md). The kit's
machinery lives under [`.claude/dprvda-kit/`](.claude/dprvda-kit/). Keep this file short
(`check_md_size` enforces a budget); link, don't duplicate.

<!-- FILL IN: one or two sentences on what this project IS, so a fresh session is oriented. -->

## Pre-commit gates (enforced on `git commit` — NEVER `--no-verify`)

Dispatcher: `.claude/dprvda-kit/gates/run_gates_parallel.py` (phase 1 serial → phase 2 parallel).

- `critic_llm` — AI judge over each staged source file. Soft-passes when `LLM_JUDGE_API_KEY` is
  unset. On a real issue it prepends `=== LLM_REVIEW_BLOCK ===` to the file (see protocol below).
- `check_file_reason` — every `.py`/`.sh`/`.rs`/… declares a `# REASON:` header (≥30 chars).
- `check_links` — every `.md` cross-reference resolves.
- `check_doc_freshness` — folder READMEs + `tracks_dir:` cascade + orphan-md contract.
- `check_md_size` — per-doc character budget.
- `check_secrets` — staged text scanned for secret-shaped strings (keys, tokens, private keys).

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

## Claude Code hooks (`.claude/settings.json` → `.claude/dprvda-kit/hooks/`)

- `block-dangerous-git.py` — blocks history-rewrite git ops (force-push, `reset --hard`,
  `clean -f`, `checkout/restore .`, `branch -D`, `filter-branch`). Normal `push` to any branch is fine.
- `check-script-launch.py` — runs the AI judge on a script before Bash launches it; blocks only on
  `severity=block`; fail-open.
- `remind-claude-md.py` — re-injects this file's critical sections on `git commit`.
- `nudge-to-*` — soft PostToolUse suggestions to use MCP tools (never block).

## Skills (`/<name>`)

`handoff` · `grill-me` · `caveman` · `tdd` · `to-issues` · `write-a-skill` · `zoom-out` ·
`audit-structure` · `compact-docs`. See each `.claude/skills/<name>/SKILL.md`.

## Critical project rules

<!-- FILL IN: the handful of domain rules a fresh session MUST know and must not re-litigate.
     e.g. "X is the only valid source for Y", "never do Z in production". Keep to the essentials —
     everything else lives in docs/. Delete this comment once filled. -->
