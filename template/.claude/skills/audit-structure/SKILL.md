---
name: audit-structure
description: Audit the repo's folder layout, file organisation, and naming conventions against the Screaming Architecture + 6-axis framework. Investigate WHY each choice was made (git log, commit messages, planning docs) before proposing changes. Use when the user asks to review project structure, check if naming/folders still make sense, audit conventions, or proposes a restructure. Do NOT shortcut to a regex check — apply the framework per item, with rationale and alternatives.
---

# REASON: Generalised structural-audit skill, because hardcoded domain words, stack-specific build conventions, and decision-log references would mislead structural audits in any other repo.

# Audit project structure

## Framework — apply consistently across audits

The audit is anchored on **two layers**, applied in order. They give
each audit a comparable scorecard so the user can diff today's
report against the last one.

### Layer 1 — Screaming Architecture (the gut check)

Robert Martin: *"Architecture should scream the domain, not the
framework."* Apply at the **top level** of the repo:

- Looking at the root `ls`, can you tell what this PROJECT does?
- Or does it just scream "this is a framework scaffold"?
- Domain words this project should scream: <list your domain's top-level concepts>
- Generic words that shouldn't dominate: `src/`, `lib/`, `utils/`,
  `helpers/` — fine if necessary, but the names INSIDE them should
  carry the domain.

Score: 🟢 screams clearly · 🟡 mixed · 🔴 generic-only.

### Layer 2 — 6-axis per-candidate scorecard

For every folder / file / naming choice flagged as a candidate,
score against six axes. Each axis: 🟢 / 🟡 / 🔴 + one-line evidence.

| # | Axis | Question |
|---|---|---|
| 1 | **Cohesion** | Do all files in this folder share a single purpose? Or does the folder mix concerns (e.g. `scripts/` mixing build helpers + test fixtures + deployment tools)? |
| 2 | **Discoverability** | Can someone unfamiliar guess where a thing lives by name alone? Or do they need to grep? |
| 3 | **Stability gradient** | Are frequently-changing files separated from stable ones? (Sprint progress != core logic != generated artifacts.) |
| 4 | **Locality of reference** | Files that change together live together? Or do edits require touching files in 5 different folders? |
| 5 | **Convention compliance** | Matches ecosystem norms for this language/framework (e.g. snake_case Python, kebab-case docs, PEP 517 layout)? |
| 6 | **Reversibility cost** | If we move this, what's the cascade? Is the choice anchored by a recent commit / planning doc that we'd be undoing? |

A candidate with **2+ red axes** is a strong proposal-to-change
case. **All-green or 1-yellow** = leave it alone, even if a
generic linter would flag the name.

**Decision-log / ADR handling (optional):** If this project maintains
Architecture Decision Records, search them before marking "no recorded
reason". Location varies by project — common paths: `docs/decisions/`,
`docs/adr/`, `adr/`. If no ADR directory exists, decisions live in
commit messages and `docs/planning/`.

## Process

### 1. Gather the picture

- `tree -L 3 --gitignore` (or equivalent on Windows: `cmd //c "tree /F /A | head -200"`).
- `git log --diff-filter=R --name-status --since='90 days ago'` —
  recent renames / moves.
- Read `CLAUDE.md` — what the surviving authored docs CLAIM the
  structure is.
- Skim recent commit messages + `docs/planning/` for structural
  decisions and their rationale.

### 2. Apply Layer 1 (Screaming Architecture)

Write a 3-sentence verdict on the root layout. Score 🟢 / 🟡 / 🔴.
Note specifically what screams domain vs framework.

### 3. Surface candidates and apply Layer 2

Walk top-down (root → first-level dirs → second-level). For each
candidate, write a scorecard:

```
### <area> — <one-line summary>

**Today**: <what exists>
**Why (best as I can tell)**: <commit/planning-doc/ADR link, or
"no recorded reason found">

**Scorecard:**
| Axis | Score | Evidence |
|---|---|---|
| 1 Cohesion | 🟡 | scripts/ holds 4 gate scripts + 5 export tools + bootstrap |
| 2 Discoverability | 🔴 | new contributor wouldn't guess `scripts/check_*.py` is the gate suite |
| 3 Stability gradient | 🟢 | gates change rarely, exporters change with sprint cadence — separated already |
| 4 Locality | 🟡 | gate edits cascade to .pre-commit-config.yaml + session-bootstrap.sh, both at root — fine |
| 5 Convention | 🟡 | Python ecosystem norm is `tools/` or `bin/`, not `scripts/` for mixed content |
| 6 Reversibility | 🔴 | 4 pre-commit-config refs + 1 settings.json hook + 5 sibling .mds + 8 cross-doc links |

**Proposal**: <concrete change>
**Cost**: <files touched, downstream effects, estimated session-time>
**Alternatives considered**: <what else>
```

### 4. Investigate WHY for each red/yellow axis

Before proposing a change, run the investigation:

- `git log --follow -- <path>` — when introduced, what message?
- `git log --all -- <similar-paths>` — was the alternative ever
  tried and reverted?
- Search ADRs / planning docs for an existing rationale (if maintained).
- If "no recorded reason" — say so explicitly. Don't assume it
  means "no reason"; ask the user.

### 5. Group proposals by likely-acceptance

- **Easy wins** (rename + update <5 cross-refs)
- **Medium** (refactor a folder, update nav + sibling .mds + a few imports)
- **Big** (restructure a module; many files; tests, scripts, docs cascade)

Big proposals belong at the top of the report with explicit cost
framing.

### 6. Save the report

Write to `docs/planning/structure-audit-<YYYY-MM-DD>.md`. Each new
audit appends a new file (don't overwrite) so the user can diff
audit-vs-audit and see structural drift over time.

### 7. Don't shortcut to action

End with: `Ready. Pick which proposals to act on, in which order.`
Don't pre-commit any changes. Wait for the user's go-ahead per
proposal. **Don't be afraid of long reworks** if authorized — Claude
has time to do them correctly.

## What to surface explicitly in the report

Always say:

- **Layer 1 verdict** (Screaming score + evidence)
- **Top 3 candidates** (cost-vs-payoff)
- **What you decided NOT to flag** + one-line reason — proves you
  considered the obvious targets
- **What's locked** (ADRs / planning pins if the project maintains them) — intentionally
  untouchable
- **Diff vs the previous audit** if `docs/planning/structure-audit-*.md`
  files exist

## Anti-patterns to avoid

- Treating an industry convention as an automatic rule. Match the
  project's stage and constraints first.
- Proposing renames without checking the cascade (folder READMEs,
  nav config, pre-commit gate paths, import paths in code, cross-doc links).
- Burying a big proposal in the middle of small ones.
- Stopping at "this looks weird". Always explain *what* better
  would look like and *why*.
- Asking the user to read a 50-item list. Cap at ~10 candidates
  per audit.
- Auto-applying scorecard advice. Always wait for user go-ahead.

## Related

- `.claude/commands/audit-structure.md` — slash-command wrapper for
  on-demand invocation.
- `CLAUDE.md` "Pre-commit gates" — the audit complements those
  gates (which catch per-file drift) by catching structural drift
  the gates can't see.
