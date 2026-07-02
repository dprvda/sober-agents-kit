---
name: compact-docs
description: Compact, consolidate, trim, and fact-verify over-budget Markdown docs down to their check_md_size WARN threshold (the 15%-headroom line), so a working session keeps room to add new content before hitting the BLOCK cap. Use when docs are warn-flagged by check_md_size, when the user asks to compact / trim / tighten / consolidate docs, or to reclaim doc headroom before or after a doc-heavy session.
---

# REASON: Generalised compact-docs skill, because project-specific tier names were hardcoded and the size-gate script path must point at the kit's gate location.

# Compact docs

Bring every over-budget Markdown doc down to its **WARN** threshold — not merely under BLOCK — and fact-verify it against the code on the way. This is the counterpart to the `check_md_size.py` gate: the gate flags, this skill remediates.

## Why WARN, not BLOCK

`check_md_size.py` sets two lines per tier: **WARN** (the 15%-headroom line) and **BLOCK** (the hard chunk-aligned cap). A doc sitting at BLOCK has zero headroom — the next edit that grows it blocks the commit. A session continuously *adds* data to docs; without headroom every doc touch becomes a compaction fight. Trimming to WARN restores ~15% room so the session can grow docs freely. WARN itself never blocks a commit — this skill is doc hygiene, not gate-unblocking.

## Quick start

```bash
python .claude/dprvda-kit/gates/check_md_size.py     # every WARN + BLOCK row is a target
```

Each flagged row prints `chars/BLOCK [tier]`. The goal is that tier's WARN number. Walk each flagged doc to ≤ WARN.

## Process — one agent per doc, worktree-isolated

Parallelise: launch one agent per doc with `isolation: "worktree"`, so each works in its own git worktree with no shared working tree to race on. The orchestrator then collects each finished doc from its agent's worktree — distinct docs merge conflict-free. **Never** run parallel edit-agents on the *shared* checkout: concurrent edits there silently revert each other. Worktree isolation is the fix — not sequential execution.

Each agent does, for its doc, in this order:

1. **Verify** — read it top-to-bottom against the code it documents. Fix every drifted claim: stale counts, renamed symbols, changed behaviour, dead paths. A doc you have not fact-checked must not be trimmed — you cannot tell filler from fact, and a confidently-wrong doc is worse than a merely stale one.
2. **Consolidate** — merge duplication. A fact stated twice in the doc → once. A fact that already lives in another doc / decision record / code → cross-link, don't restate (DRY).
3. **Compact** — drop filler ("it's worth noting", "this section describes"); verbose prose → tight bullets; parallel facts → tables; ≤1 Mermaid per doc.
4. **Trim** — only if still over WARN after 1–3. Cut the least-load-bearing content first, ranked: point-in-time changelogs, "pre-#NNN it used to do X" history, resolved-incident detail already preserved in a decision record / lessons file, bare commit hashes (`git log`-derivable), perf numbers that belong in benchmark output.

## Hard rules

- Steps 1–3 are lossless — every fact survives. Only step 4 deletes, and only least-valuable-first.
- **Never delete a current-behaviour fact, a decision record/issue reference, or a gotcha to hit a number.** If a doc cannot reach WARN without that, stop at its lossless floor and report the gap — do not amputate.
- Keep YAML frontmatter intact; keep every markdown cross-link resolving.
- A doc on its own deliberately-higher cap tier is trimmed to redundancy only — never below its facts.

## Finish

Re-run `python .claude/dprvda-kit/gates/check_md_size.py`. Confirm no WARN/BLOCK rows remain, or report exactly which docs stopped at a lossless floor above WARN and which facts blocked them.
