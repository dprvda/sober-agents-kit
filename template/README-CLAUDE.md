---
tracks_dir:
  - .claude/dprvda-kit/hooks/
  - .claude/skills/
  - .claude/commands/
  - .claude/settings.json
  - CLAUDE.md
  - .claude/dprvda-kit/gates/
  - .pre-commit-config.yaml
---
# Claude Code setup — what's special about this repo

Manual for ~3 layers of Claude Code customisation not in vanilla `claude-code`. All version-controlled — `.claude/` is **tracked**, so a clone gives the same environment. This repo treats Claude Code as a *disciplined* partner, not free-form chat:

> - **PreToolUse Bash hooks** — physically block dangerous git ops, unmarked script launches.
> - **Pre-commit gates** (strict, no bypass flags) — force doc + code-quality reviews before every commit.
> - **Self-defending canary** re-tests the doc-freshness gate whenever its script is edited.
> - **Project rules** in `CLAUDE.md` (refreshed every commit by a hook).
> - **Custom skills** (`/handoff`, `/tdd`, `/compact-docs`, …) for repeatable multi-step workflows.

The AI-judge prompt (`.claude/dprvda-kit/gates/prompts/critic_llm.md` + the per-project `project-context.md`) stays in sync with `CLAUDE.md`'s critical-domain rules — a rule rewrite updates all surfaces in one commit, so judges flag re-introduced removed code paths. Judge env vars: `LLM_JUDGE_API_KEY`, `LLM_JUDGE_BASE_URL`, `LLM_JUDGE_MODEL` — any OpenAI-compatible host; the recommended free judge is the NVIDIA build endpoint (see `.env.example`). In-source marker: `=== LLM_REVIEW_BLOCK ===`. Sidecar dir: `.llm-review/`.

---

## Quick start (after `git clone`)

```bash
# one-time pre-commit infra, then wire hooks
pip install pre-commit pyyaml
pre-commit install
cd <repo-root> && claude   # open in Claude Code
```

`.claude/settings.json` (committed) auto-wires the PreToolUse Bash
hooks; `.pre-commit-config.yaml` wires the gates.

---

## Layer 1 — `.claude/` directory (everything tracked)

`settings.json` wires the PreToolUse Bash hooks (`settings.local.json` =
gitignored user-local overrides); `hooks/` = Python hooks fired on tool
use; `skills/` = multi-step workflows; `commands/` = slash commands.

### Hooks (PreToolUse Bash blockers + PostToolUse soft nudges)

PreToolUse blockers chained in `settings.json` under
`hooks.PreToolUse[Bash]` — each reads tool input as JSON on stdin and
exits 2 + stderr message to block. PostToolUse soft nudges under
`hooks.PostToolUse[{Bash,Grep,Read}]` — each emits a JSON
`hookSpecificOutput.additionalContext` record and always exits 0
(never blocks; informational signal to the model). Full context in
each hook's `# REASON:`.

| Hook | What it blocks | Bypass |
|---|---|---|
| `block-dangerous-git.py` | `git push --force/-f`, `--mirror`, `--delete`, `reset --hard`, `clean -f`, `checkout/restore .`, `branch -D`, `filter-branch`, `reflog expire`. Normal `git push` to any branch is allowed. | none — physical block |
| `check-script-launch.py` | `python foo.py` / `bash foo.sh` / `./foo.{py,sh,bash}` whose target the AI judge (`critic_llm.py`, working-tree mode) returns `severity=block` on. On warn/block the judge prepends an in-source `=== LLM_REVIEW_BLOCK ===` comment + the hook surfaces the sidecar JSON path. | fail-open — judge unreachable / key missing / timeout / rc=2 → launch allowed. Unblock a real `block`: read the REVIEW_BLOCK, fix the line-numbered issues, drop the block, re-run. |
| `remind-claude-md.py` | nothing (passes silently); fires on `git commit`, re-injects critical `CLAUDE.md` sections to stderr | n/a |
| `nudge-to-foreground-git.py` | nothing — soft `PostToolUse:Bash` JSON-additionalContext nudge fires when a `git commit` / `git push` / `pre-commit run` is dispatched with `run_in_background=true`. Suggests the foreground pattern which keeps commits at the ~20s baseline rather than perceived 5+ min hangs. | n/a (always exit 0) |

### Skills

A "skill" is a multi-step workflow Claude invokes by name; each lives in
`skills/<name>/SKILL.md`, auto-listed in the system prompt.

| Skill | When to use |
|---|---|
| `handoff` | About to clear context — generates a PASS-AI handoff file + commits + pushes |
| `audit-structure` | Periodic Screaming Architecture + 6-axis structural review |
| `grill-me` | Stress-test a plan — Claude interrogates you on every branch |
| `caveman` | Compress communication ~75% by dropping articles/filler |
| `tdd` | Red-green-refactor loop with tests |
| `to-issues` | Break a plan into independently-grabbable GitHub issues |
| `write-a-skill` | Bootstrap a new skill with proper structure |
| `zoom-out` | Re-orient after a deep dive (broader-context map) |
| `audit-and-fix` | Triage a multi-runner test suite end-to-end — full audit, deep-analysis card-writing agents, local HTML review UI, AI consolidation pass, GH issue filing, impl agents. |
| `compact-docs` | Trim over-budget Markdown docs back to their `check_md_size` WARN threshold |

### Slash commands

`commands/<name>.md` registers `/<name>` in the chat with an
instruction template.

| Slash | What it does |
|---|---|
| `/handoff` | Wraps the handoff skill (commits + writes PASS-AI handoff file) |
| `/audit-structure` | Wraps the audit-structure skill |
| `/audit-and-fix` | Wraps the audit-and-fix skill — multi-stage test-suite triage with card review UI |

---

## Layer 2 — Pre-commit gates (strict, no bypass flags)

Wired in `.pre-commit-config.yaml`, run on every `git commit` via
`.claude/dprvda-kit/gates/run_gates_parallel.py` (`PHASE1_GATES + PHASE2_GATES` =
authoritative roster). **Two phases:** Phase 1 — serial, fail-fast,
mutates the working tree (code discipline): `critic_llm` →
`check_file_reason`. Phase 2 — parallel (ThreadPoolExecutor,
read-only): remaining gates; skipped when phase 1 blocks.

The AI judge runs an `unavailable_pass` (rc=0 + stderr warning)
when the judge API is unreachable / key missing / retry exhausted, so
an offline day still ships. A real `severity=block` blocks the commit —
**never `--no-verify`**.

### Phase 1 — code-discipline gates (2)

| Gate | What it enforces |
|---|---|
| `critic_llm.py` | **AI judge.** Reviews each staged `.py`/`.sh` against a project-aware rubric; returns `{ok, warn, block}`. On warn/block prepends `=== LLM_REVIEW_BLOCK ===` to the working-tree file (`--no-mutate` suppresses). Sidecar cache `.llm-review/<path>.json` keyed on sha256 of clean content. `unavailable_pass` on API miss/timeout. Same script runs `--files <target> --no-mutate` from `check-script-launch.py`. No bypass on `severity=block`. |
| `check_file_reason.py` | Every script (`.py`/`.sh`/`.bash`) declares WHY it exists at the top via `# REASON:` — ≥30 chars + a substantive token (`vs`, `instead of`, `because`, `to enable`, `replaces`, `forces`, `no existing`, `needs review`). Forces reuse-vs-create thinking. |

### Phase 2 — doc-drift + lint gates (enabled set)

| Gate | What it enforces |
|---|---|
| `check_links.py` | Every `.md` cross-reference (target file + anchor) resolves. Native md parser, no subprocess. |
| `check_doc_freshness.py` | Two active checks. **Pass C `tracks-dir`** (session-bounded) — fires when BOTH a file in the `.md`'s `tracks_dir:` is newer than the `.md` AND a `.claude/handoffs/handoff_*.md` is staged in the current commit; so a commit that stages no handoff never fires Pass C — the cascade surfaces only at session-wrap. **Pass D `orphan-md`** — every authored `.md` declares ONE of `tracks_dir:` / `frozen_at:` / `derived_from:`. Uses `effective_mtime = max(fs_mtime, git_commit_ts)` via `_git_mtime.py`, strict. `--ack-no-drift PATH --reason '<≥30 chars>'` is the audit-logged escape for pure mtime ripples with no body drift. |
| `check_md_size.py` | Per-doc **character**-budget gate. Each tier declares a BLOCK cap; WARN is derived `round(block×0.85)` (uniform 15% headroom). Caps map 1:1 onto the 10000-char SessionStart injection chunk. Tiers: `claude-md` 16800, `essential` (every `docs/*.md`) 19500, `handoff` 19500, `per-module-readme` 9500, `framework-rules` 19500, `other` 14400. `EXEMPT_PREFIXES` skips `archive/`, `docs/archive/`, `docs/planning/`, `target/`, `site/`; handoffs NOT exempt (own `handoff` tier). |
| `check_handoff_schema.py` | Triggers only when a `.claude/handoffs/handoff_*.md` is staged (else instant no-op). Asserts the §1.5 Data-state schema has all mandated fields populated. Pre-schema handoffs skipped. |

**Optional gates** (enable per-project as needed):

| Gate | What it enforces |
|---|---|
| `critic_llm_commit.py` | **AI judge on commit message.** Validates Conventional Commits format, then sends message + staged diff to the judge (type↔diff alignment, scope↔paths, body adequacy, `BREAKING CHANGE:` shape). `unavailable_pass` on outage. |
| `check_cargo_audit.py` | RustSec advisory gate over the transitive dep set (Rust projects). |
| `check_cargo_vet.py` | Supply-chain trust gate via `cargo vet` (Rust projects). |

Conventional Commits scopes (examples — edit to match your project):
`core|cli|api|ui|docs|build|ci|deps|meta`

### Self-defending canary (gate-scoped)

`test_check_doc_freshness.py` fires when `check_doc_freshness.py` or the
shared `_git_mtime.py` helper changes — builds a tmp git repo with
backdated commits + FS mtimes, runs the gate, asserts the right files
flag. Catches parser regressions that silently let drift through.
`_git_mtime.py` is the single source of truth for `effective_mtime`.

### Commit-msg + post-commit hooks (separate from the gate roster)

| Hook | Stage | What it does |
|---|---|---|
| `apply_tag_trailer.py` | `post-commit` | If HEAD's message has a `Tag: vX.Y.Z` trailer, runs `git tag -a <tag> HEAD -m <subject>`. Idempotent on amend, never crashes. |

---

## Layer 3 — Project conventions (`CLAUDE.md`)

`CLAUDE.md` (repo root) is **rules-only**. State, architecture, reference docs live under `docs/` (decisions in `docs/decisions/`); gate roster + per-tier numbers live in **this file**, linked not duplicated. `remind-claude-md.py` re-prints its critical sections to stderr on every `git commit`. Global `~/.claude/CLAUDE.md` carries universal rules; both files re-inject every commit.

Key sections (adapt per project): pre-commit gates · NO-bypasses ban-list · `archive/` out-of-context · Tempo (deadlines fit dozens of tasks) · critical domain rules · pre-approved autonomous ops · PreToolUse hooks · skill/slash commands.

---

## Doc-drift control framework

`check_doc_freshness.py` (Pass C/D mechanics in its gate row above) is
the per-commit anchor — `.md` drift is the failure mode where the next
AI session trusts a stale doc and wastes context. **Fix discipline:**
when a doc's `tracks_dir:` source changes (Pass C fires on handoff-staging commits; Pass D enforces the frontmatter contract on every authored .md — folder-README presence checks exist in the script but are NOT active), Read the doc
top-to-bottom, compare to current source, **rewrite wherever drift is
found** — the body edits ARE the proof of reading. The gate's stderr
prints this at the top, so an AI session sees it AT triage time.

---

## Replicating this in your own repo

1. **Copy `.claude/`** — hooks, skills, slash commands for free.
2. **Adapt `CLAUDE.md`** — your own rules-only file; keep it short.
3. **Copy `.claude/dprvda-kit/gates/check_*.py` + `_git_mtime.py`** — start with
   `check_doc_freshness`, `check_file_reason`, `check_links`,
   `check_md_size`; adapt the exempt-dir list.
4. **Copy `test_check_doc_freshness.py`** — the canary protects the
   freshness gate from silent regressions.
5. **Copy `.pre-commit-config.yaml`**, then `pre-commit install`.
6. **Set `__PROJECT_NAME__`** throughout and update scope list in
   `check_file_reason.py` / commit-msg gate.

Each gate/hook here targets a real autonomous-session failure mode
(force-push under pressure, `--no-verify`, stale docs, duplicate
scripts, forgotten rules) — turning "what an AI thinks it should do"
into "what the system allows", ratcheting up as new failure modes get
caught.

---

## See also

- `CLAUDE.md` — project rules (always loaded) · `~/.claude/CLAUDE.md` —
  universal discipline rules
- `.claude/dprvda-kit/docs/context-framework.md` — doc-authoring tiers + freshness cascade
- `.claude/dprvda-kit/docs/parallel-agents.md` — multi-agent worktree discipline + cwd-drift rules
- `docs/decisions/README.md` — ADR index
- `.pre-commit-config.yaml` + `.claude/settings.json` — gate/hook wiring
- `.claude/dprvda-kit/gates/run_gates_parallel.py` — authoritative gate roster
