---
frozen_at: 2026-07-02
---
# Third-party skills/hooks/plugins — hands-on evaluation (2026-07-02)

Every pack below was cloned, read in full, and (where runnable) executed on this machine.
This doc is the kit's sourcing map: what we vendor, what we graft as patterns, what we link.

## License matrix (vendor = copy files into this kit; graft = reimplement the pattern; link = point only)

| Pack | Stars | License / holder | Call | Obligation |
|---|---|---|---|---|
| obra/superpowers | official marketplace | MIT / Jesse Vincent | VENDOR select skills | carry LICENSE text |
| OthmanAdi/planning-with-files | 24.3k | MIT / Ahmad Adi | GRAFT hooks patterns | notice if files copied |
| DietrichGebert/ponytail | 71.2k | MIT / DietrichGebert | GRAFT ladder + hooks | notice if files copied |
| ccusage/ccusage | 16.8k | MIT / ryoppippi | LINK (npm tool) | none (not vendored) |
| anthropics/skills frontend-design | — | Apache-2.0 per-skill | VENDOR ok | keep LICENSE.txt + NOTICE |
| anthropics/skills docx/pdf/pptx/xlsx | — | source-available ONLY | LINK ONLY | never vendor |
| nikolasdehor/visual-eyes | — | MIT / Nikolas DeHor | VENDOR ok | carry notice |
| cc-safe-setup (npm) | upstream deleted | MIT declared, NO license text in tarball | LINK/reimplement only | avoid verbatim files |
| pyramidheadshark/claude-scaffold | ~4 (npm real) | MIT | design reference | — |
| rohitg00/awesome-claude-code-toolkit | 2.2k | Apache-2.0 + vendored MIT inside | ideas only — 10/20 hooks are BROKEN (argv-not-stdin no-ops) | if copying: Apache text + nested attributions |

## Kit update plan (keep / graft / vendor / drop)

VENDOR (with MIT notice, clauses rewritten for our ship-to-main + never-stop-to-ask doctrine):
1. superpowers/subagent-driven-development (+ implementer/reviewer templates + task-brief/review-package scripts) —
   file-handoff economics, 4-status escalation contract, dual-verdict diff-only review, durable progress ledger.
2. superpowers/receiving-code-review — the anti-sycophancy skill (no equivalent in the kit).
3. superpowers/systematic-debugging — 4 gated phases + the 3-failed-fixes → question-architecture breaker.

GRAFT (patterns, no files):
- TDD armor into our `tdd`: rationalization table, red-flags list, delete-means-delete, verify-RED/verify-GREEN.
- writing-skills method into `write-a-skill`: baseline-fail-first skill testing, Match-the-Form-to-the-Failure,
  description = trigger only (audit our own skills for workflow-summarizing descriptions — several violate it).
- brainstorming's one-question-at-a-time + HARD-GATE + spec self-review into `grill-me`.
- writing-plans' fleet-plan format (Interfaces Consumes/Produces, Global Constraints verbatim, no-placeholder list).
- SessionStart router-inject pattern (tiny always-on router on startup|clear|compact; bodies pull-load) — the
  superpowers wiring trick; pairs with our inject_context_docs.
- ponytail's 7-rung need-to-exist ladder + `// ponytail:`-style named-ceiling comments + SubagentStart
  re-injection (subagents skip CLAUDE.md; user-level + SubagentStart hooks reach them).
- planning-with-files: PreCompact flush hook, gated Stop-hook with stall-detection + block cap (the AFK-run
  guard), SHA-256 plan attestation before unattended loops.
- cc-safe-setup ideas: user-level install for subagent coverage, incident-receipt catalog per guard,
  cd+git auto-approver; toolkit's compound-command decomposition for our block-dangerous-git (defeats
  `cd x && dangerous` bypasses).
- claude-scaffold's cross-repo registry + `update --all` drift sync — the model for our kit.config.json
  update story; bash-output-filter (wrap verbose commands, feed ~20 relevant lines).

DROP/SKIP: superpowers using-git-worktrees + finishing-a-development-branch (native worktrees + ship-to-main),
executing-plans (filler), awesome-claude-code-toolkit hooks as-is (broken input handling).

## Verified-by-running notes
- ccusage 20.0.14: ran against this machine's real `~/.claude/projects` JSONL — correct daily totals; Rust core,
  global dedupe by message.id+requestId incl. sidechain replays.
- visual-eyes: installed; its screenshot.sh captured a live prod page via Playwright first try.
- superpowers 6.1.0: installed via `claude plugin install superpowers@claude-plugins-official`; 715 always-on
  tokens; one SessionStart hook; per-skill costs via `claude plugin details superpowers`.
- Plugin CLI: `claude plugin details <name>` (projected token cost) and `claude plugin eval` (graded eval runs,
  with a no-plugin baseline arm) are the underused native surfaces for auditing any pack before adopting it.
