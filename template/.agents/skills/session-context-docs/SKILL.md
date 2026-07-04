---
name: session-context-docs
description: Use when setting up or auditing the docs that inject into every AI session so a fresh agent has full-project visibility (where to look, what to open and edit for any feature). Triggers on "docs injected at session start", "living orientation docs", "full visibility for new sessions", onboarding a project's context map, or noticing agents re-read source to orient every session.
---

# REASON: Generalized setup procedure for the session-injected orientation-doc set, because the concrete docs are project-specific but the method — many small file-scoped living docs, flat in docs/*.md so the injector picks them up, one tracks: contract each, and verified chunk-slot headroom — is universal; the existing context-framework.md covers authoring STYLE but nothing covers standing up the injected SET or its wiring. Uses __PROJECT_NAME__ and kit-relative paths.

# Session context docs

## Overview

A set of small, **file-scoped living orientation docs** that auto-inject at every new/cleared/compacted session, kept fresh at file granularity by the doc-freshness gate. A fresh agent reads the injected map instead of re-deriving orientation from source.

**Core principle: one concern per doc; each doc owns exactly the file(s) it describes; every claim traces to current code.** Authoring *style* (tiers, citations, facts-only) lives in `.agent-kit/docs/context-framework.md` — read it. THIS skill is how you stand up and wire the injected set.

## When to use

- Standing up a project so any new session starts with a full map.
- Auditing or expanding an existing injected-doc set.
- Symptoms: agents re-read source to orient each session; "where does X live?" asked repeatedly; one big stale README nobody trusts.

**Not for:** one-off state (use `/handoff`); historical snapshots (use `frozen_at:`); API reference the code already is.

## The mechanism (kit-provided — don't rebuild it)

- `.agent-kit/session/inject_context_docs.py` globs **`docs/*.md`** (flat, non-recursive) and slices the corpus into ≤9800-char chunks; `.claude/settings.json` runs one SessionStart hook per `--chunk N` slot.
- `.agent-kit/gates/check_doc_freshness.py` enforces the `tracks:` freshness contract per doc.

So a doc auto-injects **the moment it exists at `docs/<name>.md`** — no per-doc config. Your job is the set, the contracts, and the slot headroom.

## The recipe — what a proper set IS

1. **A map doc first** (`docs/architecture.md`): what the system is, its top-level parts one line each, and a **"where to look" index linking every other doc.** Author it first so the rest link back to it.
2. **One doc per subsystem/concern**, small (≤~120 lines): schema, queue, each pipeline stage, routes, auth, etc. Split by what changes together, not by technical layer.
3. **Flat in `docs/`.** The injector globs `docs/*.md` non-recursively — a nested `docs/db/schema.md` will **not** inject.
4. **Each doc declares `tracks:`** — the file(s) or directory it owns. **Prefer file-level** (`tracks: packages/db/src/schema.ts`) so only that doc flags when that file changes; use a directory only when every file under it affects the doc's claims.
5. **Pointer style, facts-only.** Purpose, key files/symbols, "where to edit for X", gotchas, links. Not a tutorial, not a restatement of code. Verify every claim against current source as you write. Roadmap/aspirational content goes **only** in a clearly-labeled `strategy.md`/`roadmap.md`.

## Required verification (run ALL — silence is not success)

| Check | Command | Must show |
|---|---|---|
| Slot headroom | `python .agent-kit/session/inject_context_docs.py --count` vs `grep -c -- "--chunk" .claude/settings.json` | count ≤ slots (add `--chunk N` slots + spares if not — **otherwise chunks are silently dropped every session**) |
| Every doc injects | `python .agent-kit/session/inject_context_docs.py --all \| grep "====="` | each `docs/*.md` as its own section |
| Contracts + no orphans | `python .agent-kit/gates/check_doc_freshness.py --json` | no `orphan-md` / `deprecated-tracks-key` |
| Map links resolve | `python .agent-kit/gates/check_links.py` | 0 broken cross-references |

## Common mistakes

| Mistake | Fix |
|---|---|
| A few big docs | Many small file-scoped docs, one concern each |
| Doc under `docs/sub/dir/` | Flat `docs/*.md`, or it never injects |
| `tracks:` a dir that mixes source + tests | `tracks:` the specific file(s) so only real changes fire |
| Authored, never checked `--count` vs slots | Silent chunk drop — verify slot headroom every time |
| Tutorial / aspirational prose | Pointer + facts-only; roadmap goes in `strategy.md` |
| No contract declared | Pass D blocks — add `tracks:` / `frozen_at:` / `derived_from:` |

## Red flags — stop

- "I'll put it all in one big `ORIENTATION.md`." → No. Granular = precise freshness + no injection bloat.
- "It'll inject wherever I put it." → Only flat `docs/*.md` injects.
- "`tracks:` the whole folder is close enough." → It over-fires on unrelated changes; track the exact file(s).
- "Looks done." without running `--count`, `--all`, and the freshness gate. → Not done until verified.
