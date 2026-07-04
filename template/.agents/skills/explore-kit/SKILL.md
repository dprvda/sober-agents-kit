---
name: explore-kit
description: Explore and understand the sober-agents-kit installed in THIS repo — the commit gates, session memory, hooks, skills, and how to work under them without fighting them. Trigger on "explore the kit", "what is .agent-kit", "how do the gates work", "understand my agent setup", "what does the kit do".
---

# /explore-kit — a map of the sober-agents-kit you are working under

This project was set up by [sober-agents-kit](https://github.com/dprvda/sober-agents-kit) — machinery
that turns "what an AI thinks it should do" into "what the project allows." It is generic and shared
across many projects; it holds NO project-specific mission and NO keys (see the last section). Use
this skill to learn where everything is and how to work with it, then get out of its way.

## The one rule that matters most

**The gates are law. Never bypass them (`--no-verify`, disabling a test, `assert True`, swallowing an
exception). If a gate blocks you, fix the cause, not the gate.** Everything below serves that rule.

## The layout (walk it top-down)

- **`AGENTS.md`** (repo root) — THE standing rules file, read natively by every agent tool. Short,
  judgment-first. `CLAUDE.md` is a one-line bridge that imports it. **Read this first, every session.**
- **`.agent-kit/`** — all the machinery, in one namespaced folder:
  - `gates/` — the commit gates + the AI judge + their prompts. `gates/README.md` explains each gate
    and the block protocol. `run_gates_parallel.py` is the dispatcher.
  - `session/` — session memory. `inject_context_docs.py --all` prints the project "spine" (key docs,
    live progress, recent state). Run it at the start of every session before anything else.
  - `frameworks/` — short, verified fact-sheets about the tools this project uses (one file per tool).
    Read the relevant one before writing code against that tool.
  - `stack-guides/` — patterns for the project's chosen stack.
  - `adapters/` — per-tool wiring (e.g. the Claude live-hooks adapter). Only the adapter for your tool
    is active.
- **`.pre-commit-config.yaml`** — wires the gates to run on every `git commit` (and pre-push).
- **`.claude/`** (only if this is a Claude Code project) — the settings + a mirror of the skills.
- **`.agents/skills/`** — the skill set (this file is one of them), read natively by other tools.

## The commit gates (run on every `git commit` — protect every tool)

Read `.agent-kit/gates/README.md` for the current roster and exact thresholds. In spirit they block:
key-shaped strings (a leaked key in the diff); scripts with no `# REASON:` header (forces reuse-vs-create
thinking); docs that have drifted from the code they describe; broken markdown cross-references; and an
independent **AI judge** that reviews each staged source file against the project's rules. On a judge
warn/block, a `=== LLM_REVIEW_BLOCK ===` header is prepended to the file — read the listed items, fix
them, remove the block, re-stage, re-commit. When the judge's API is unreachable it soft-passes, so an
offline day still ships; a real `block` blocks — fix it.

## Session memory (so a fresh session isn't lost)

The AI's memory is wiped between sessions. `.agent-kit/session/inject_context_docs.py --all` reprints
the project spine so a new session re-orients instantly; `AGENTS.md`'s first instruction tells every
agent to run it. Pair it with the `handoff` skill when wrapping up: verified progress notes out, a
briefed next session in.

## The live hooks (Claude adapter, if present)

`.agent-kit/adapters/claude/` adds in-session hooks that physically block dangerous git (force-push,
`reset --hard`, `branch -D`) BEFORE git even runs, and review a script before it launches. These are a
safety floor, not a nuisance — if one fires, you were about to do something the project forbids.

## The skills

The skills mirrored into `.agents/skills/` (and `.claude/skills/`) are saved procedures you invoke by
name (`handoff`, `tdd`, `grill-me`, `audit-structure`, `zoom-out`, `compact-docs`, `to-issues`,
`write-a-skill`, `sober-setup`, and this one). Read a skill's `SKILL.md` before using it.

## Where the PROJECT lives (NOT in the kit)

The kit is generic. THIS project's actual mission, product spec, and its own configuration live in the
**project's own docs at the repo root** — read `NORTHSTAR.md` (what the product is), `CUSTOMER-TRUTH.md`
(what "done" means), and `INFRASTRUCTURE.md` (the decided stack, and the pointer to where this project's
keys are kept). The kit never contains a project's keys or private values, and you must never add them
to it: **the kit is public** — keys and private info belong only in the project's own private docs and
its local, uncommitted environment. When you need a key, follow `INFRASTRUCTURE.md`; do not put key
names, locations, or values anywhere under `.agent-kit/` or `.agents/`.
