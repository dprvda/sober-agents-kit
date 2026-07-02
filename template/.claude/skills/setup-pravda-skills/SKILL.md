---
name: setup-pravda-skills
description: Interactive installer + auditor for the sober-agents-kit. Interviews the user about their project (what it is, stack, scopes, enforcement level, judge provider), then installs and configures exactly the hooks/gates/skills that fit, writes the judge's project context, proposes vetted third-party skill packs with install commands, and emits a personal how-to-work cheatsheet. Run it in a NEW project to set up from zero, or in an already-kitted project to audit/update the setup. Trigger on "/setup-pravda-skills", "set up the kit", "install the claude code kit", "audit my claude setup".
---

# /setup-pravda-skills — the interview-driven kit installer

You are setting up (or auditing) a project's Claude Code discipline layer. The kit's machinery
lives in this repo under `template/`; `install.py` copies it. Your job is everything `install.py`
cannot do: ask the right questions, derive the right configuration, write the per-project pieces
by hand, and leave the user with a cheatsheet instead of a README maze.

**The one rule that shapes every answer** (from the 2026 operator research): *a hook enforces, a
skill teaches, a subagent isolates, CLAUDE.md routes.* Anything correctness-critical goes in a
hook (even triple-documented advisory rules get ignored). Anything the user retypes goes in a
skill. Keep the installed skill count ≤ ~12: at ~20 similar skills agents pick the wrong one, and
in one field test 40 of 47 installed skills made output worse.

## Stage 1 — the interview (AskUserQuestion, two batches)

**COLD-USER LANGUAGE (binding, every message):** assume a newbie who has never heard of TDD,
MCP, worktrees, or "session continuity." Every proposed item is described by its OUTCOME in plain
words ("the AI writes a test before code, so bugs are caught immediately"), never by insider
shorthand. A technical term may appear only WITH its plain-words gloss in the same line.

**THE COMPONENT WALK (the interview's shape):** for EVERY component the kit touches, do all
four, in order: EXPLAIN it in cold-user words (what it is, why it exists) → PROPOSE the concrete
setup derived from their answers → SET IT UP → SHOW HOW TO USE IT (one worked example, which also
lands in the cheatsheet). Components: the instruction files (AGENTS.md/CLAUDE.md), the commit
gates, the AI judge, the session system (docs auto-load + progress ledger), skills, MCP, stack.
Nothing gets installed unexplained; nothing gets explained without a usage example.

**Universal question protocol (every question, both batches):** each question ships with a
one-line WHY, one example answer, and the standing offer: "unsure? say ASK ME and I will interview you for this one question — short
follow-ups until we have the answer — or just answer roughly and I refine it." A vague answer is never rejected: draft the
refined version yourself (e.g. turn a loose project description into candidate never-violate
rules) and present it for confirmation. Nothing is final until the pre-install SUMMARY, where
every derived decision is shown once and the user can amend any line before anything is written.


Batch A (the project):
1. **What are you building? A few plain sentences: what it does and the goal.** ONE question,
   two jobs: (a) DERIVE the archetype yourself (SaaS web app / data pipeline / content-video
   pipeline / API service / other) and confirm it in one line ("sounds like a data pipeline —
   correct me if not") — never ask the user to classify; (b) the text becomes the tailoring
   source: frame the WHY as "this answer shapes the whole setup — rules, checks, and system
   prompts get tailored to what you build" (no internal jargon). The confirmed archetype drives
   the OPTIONAL stack-guide injection (`stack-guides/<archetype>.md` → `docs/STACK.md`, CLAUDE.md
   pointer line; "other" or deferred → note as pending in kit.config.json, activatable by
   re-running). Internally the text feeds the judge's `project-context.md` + the CLAUDE.md fill-in.
2. **What are the 2-4 rules that must NEVER be violated here?** (Money movement? Data deletion?
   A public API? These become judge context + candidate PreToolUse blocks.)
3. **Stack — LEAD WITH THE PROPOSAL. By this point you know the archetype; never open with a
   quiz.** (a) EXISTING repo: detect from the files (package.json, pyproject.toml, Cargo.toml),
   confirm in one line, skip the rest. (b) NEW project: immediately present the agent-native
   default for the derived archetype from `stack-guides/` (the verified 2026 selection rule: pick
   tools by agent legibility — full API + key auth + official MCP + machine docs — e.g. a data
   pipeline gets typed Python + a container host + Neon; a SaaS app gets TypeScript/Next + Vercel
   + Neon + Stripe), one-sentence why per pick, then exactly three options: take it / name your
   own / decide later. Offer the deep-dive link for the curious: the full reasoning and
   per-archetype tables live at pravda.systems/blog/agent-native-stack-what-to-standardize-on.
   THE GUIDE IS OPTIONAL: if the stack is known/proposed, inject `docs/STACK.md` (stack + how an
   AI agent must behave on it); if the user wants to decide later, skip it and note in
   kit.config.json that the guide is pending — re-running /setup-pravda-skills activates it any
   time. Nothing else in the setup depends on it.
4. **Will multiple Claude sessions/agents work here in parallel?** (If yes: recommend native
   `claude --worktree` per stream, port/DB isolation notes in CLAUDE.md, and NO per-commit
   tagging — the kit removed its Tag-trailer hook because tags race in shared `.git` under
   parallel agents.)

Batch B (the machinery):
4a. **Docs & session memory — ASK, don't assume. Explain it as the STORY, not a feature list:**
   "Here's a problem nobody tells you about: the AI's memory is completely wiped between
   sessions. Tomorrow it remembers nothing — people lose 10-15 minutes of every session
   re-explaining their own project, every single day. The fix has two parts.
   Part 1: the project's knowledge lives in a few short docs, and every new session the AI
   automatically reads them before doing anything — like an employee who reads the team wiki
   before starting the day. You never re-explain; it just knows.
   Part 2: docs lie over time. Code changes, the doc describing it doesn't, and then the AI
   trusts a wrong doc and confidently breaks things. So every doc declares what it describes,
   and at every session HANDOFF (the wrap-up commit) an automatic check compares them: if the
   code changed but its doc didn't, the wrap-up is held until the doc is fixed. AND THE AI FIXES IT — not you. Your entire job is,
   once in a while, answering 'update the doc or acknowledge the drift?' when asked.
   This is what makes a months-long project possible. A weekend script doesn't need it."
   Then offer: FULL (reading + progress notes + the doc-check) / MEMORY-ONLY (reading + progress
   notes, no doc-check) / OFF (activatable later by re-running). Record in kit.config.json.
4b. **Which AI coding tool(s)?** Claude Code / Cursor / Codex / several. Explain the split
   honestly: the COMMIT GATES are git-level and protect you with ANY tool (they run on git
   commit, not inside the AI); the live hooks, skills, and session auto-loading are Claude Code
   features. For non-Claude or mixed: write AGENTS.md as the canonical instruction file (the
   cross-tool standard Cursor/Codex read natively) with CLAUDE.md as a one-line @AGENTS.md
   import bridge; skip the Claude-only wiring and say exactly what was skipped and why.
   THEN explain the instruction files themselves in cold words: "AGENTS.md/CLAUDE.md are the
   AI's standing instructions — the rules it reads every single session. The kit keeps them
   under ~200 lines because past that AIs start ignoring lines; must-never rules go into
   enforced hooks instead, procedures go into skills, and this file just routes." Then PROPOSE
   the starting content in Andrej Karpathy's style — say his name, it earns trust — a short numbered list of
   judgment rules drafted from THEIR answers (Karpathy's own rules file reportedly cut his AI's
   mistake rate from 11% to 3%): "if code can answer, code answers" · fail loud, never silently · read before you
   write · plus their own never-violate rules from question 2. Show the drafted file, then ask:
   keep this style, make it even more minimal, or write your own structure?
5. **Enforcement level** — Strict (all gates, judge blocking) / Standard (gates + judge
   soft-advisory) / Light (secrets + dangerous-git only). Map to install flags + gate roster.
6. **The AI judge — ASK as a want-this question:** "Do you want a separate AI judge — a second,
   independent AI that reviews every commit before it lands? The AI that wrote the code is a bad
   judge of its own work (it rubber-stamps itself); a different model catches what the author
   misses, using your never-violate rules as its checklist." Options: yes-free (NVIDIA) / yes-own
   provider / no judge (addable later). Provider details — NVIDIA build endpoint (FREE, recommended: one `nvapi-` key at
   https://build.nvidia.com, `LLM_JUDGE_BASE_URL=https://integrate.api.nvidia.com`,
   `LLM_JUDGE_MODEL=mistralai/mistral-medium-3.5-128b`) / any OpenAI-compatible host they
   already pay for / none (`--no-ai-judge`).
7. **Commit scopes** — propose a list derived from the repo's top-level folders (e.g.
   `core|api|ui|docs|build|ci|deps|meta`), let them edit. Patch `ALLOWED_SCOPES` in
   `critic_llm_commit.py` with the result.
8. **Skills to activate — a FIRST-CLASS choice, explained like the stack, never "extras".**
   Open by explaining what a skill IS in user language: saved expert procedures the AI applies on
   its own (how to test, how to debug, how to run parallel work) — they shape the QUALITY of
   everything built here. Then PROPOSE a set FILTERED FROM `.claude/dprvda-kit/skills-catalog.md` — the full catalog of
   everything the 2026-07 research (967 sources) + hands-on eval validated (kit skills, vetted
   third-party, parallel/overnight helpers, collections). Always tell the user the filter math
   ("proposing 8 of 33 — the rest didn't fit this project; full catalog: skills-catalog.md; the full study behind the menu:
   pravda.systems/blog/run-parallel-ai-coding-agents-without-babysitting").
   Under the ~12 ceiling (past
   ~12 similar skills agents pick the wrong one). Kit skills matched to the archetype and answers
   (e.g. data pipeline + parallel agents → tdd, systematic-debugging, subagent-driven-development,
   handoff, compact-docs; UI work → add visual-eyes; unsure planning → grill-me), plus the vetted
   third-party menu (Stage 3) folded in as unchecked extras with license + cost notes. The user
   confirms/edits one checklist; deselected skills are listed in the cheatsheet as add-when-needed.
9. **MCP servers** — GitHub? Serena (code navigation)? Neither (`--no-mcp`)? If Serena: ask which
   dirs hold code and patch `CODE_DIR_PREFIXES` in `nudge-to-serena.py`.

## Stage 2 — install + configure

**THE MANIFEST GATE (binding): nothing installs blindly.** Before ANY write or fetch, present the
COMPLETE manifest and get explicit confirmation: every file that will be written into their
project (grouped, with one-line purposes); every EXTERNAL fetch separately, each with its source
repo URL, license, install location (project vs user-level ~/.claude vs global npm), and why it's
needed; and the closing line "nothing else — no telemetry, no network calls except the judge API
you configured; every file is readable text." Deselected externals are listed as NOT-now with
their future install command.

1. Run `python install.py --target <path> --project-name <name> [flags from the interview]`.
2. Write `gates/prompts/project-context.md` from answers 1+2 (the judge appends it to its rubric
   automatically).
3. Fill the two `<!-- FILL IN -->` blocks in the target's `CLAUDE.md` from answers 1+2.
4. Patch `ALLOWED_SCOPES` (answer 7) and `CODE_DIR_PREFIXES` (answer 8) where applicable.
5. Write the target's `.env` as a PREFILLED TEMPLATE (from `.env.example`): base URL + model
   filled for the chosen provider, `LLM_JUDGE_API_KEY=` left blank. NEVER ask the user to paste a
   secret into the chat. Tell them exactly where to get the key, which file to open, and that
   everything soft-passes until it's filled; give the self-test command to verify afterwards.
6. Write `.claude/dprvda-kit/kit.config.json`: every interview answer + the kit commit SHA +
   timestamp. This is the update manifest — a future re-run reads it, re-asks only what changed,
   and can re-derive every generated file without clobbering hand edits.
7. EVERY doc this setup writes gets its freshness stamp: `docs/STACK.md` and `CHEATSHEET.md`
   carry `frozen_at: <install date>` frontmatter (the doc gate blocks unstamped docs). Explain the
   system to the user in plain words: "project docs carry a freshness contract — either 'this
   snapshot is dated' (frozen_at) or 'this doc must change when these folders change' (tracks_dir);
   a check on every commit keeps docs from silently rotting." Also tell them the payoff: anything
   in docs/ is auto-loaded into every fresh session (the SessionStart injection), so STACK.md's
   best practices follow the AI everywhere without re-explaining. Complete the session-system
   walk: "every fresh session auto-loads your project docs + the live progress ledger, so the AI
   never starts blind; while working it keeps notes in .claude/session-progress.md, and /handoff
   turns those verified notes into a baton for the next session." Usage example in the cheatsheet:
   'new session → it already knows the state; end of day → run /handoff'.
8. If parallel agents = yes: append the worktree ritual to CLAUDE.md (one `claude --worktree`
   per stream; contracts/migrations/lockfiles stay main-session-only; merges sequential).

## Stage 3 — propose third-party packs (links + commands only, never vendor them)

Present as a menu, install only what they pick, and warn: *Snyk found prompt injection in 36% of
tested community skills — read SKILL.md before installing, pin to a commit SHA.* Respect the
~12-skill ceiling: adding a pack usually means NOT adding another.

| Pack | What it earns | Install |
|---|---|---|
| Superpowers (obra) | full spec→TDD→subagent-review methodology | `claude plugins:install superpowers` (check its license page first) |
| Planning with Files | plan-first + save-findings-every-2-actions + session recovery | via `npx skills add` / its repo README |
| Anthropic Frontend Design | escape "Inter font, purple gradient" defaults | plugin marketplace |
| visual-eyes | Playwright screenshots so Claude sees its own UI | its repo README |
| ccusage | offline cost reports from local JSONL, zero API calls | `npm install -g ccusage` |

## Stage 4 — emit the cheatsheet

Write `CHEATSHEET.md` at the target root, personalized by the answers. Contents (adapt, don't
copy blindly): the four-phase loop (explore in plan mode → plan → implement → commit; skip
planning only when the diff fits one sentence); the placement rule; the worktree commands (if
parallel); the cost levers (`CLAUDE_CODE_SUBAGENT_MODEL=haiku`, `--max-budget-usd` on every
headless run, `.claudeignore`, `/usage` weekly); the escape hatches (`--ack-no-drift`,
`# SECRET_OK:`, `# REASON:`); what each installed gate blocks and how to fix (never bypass);
and the judge's provider + how to rotate its key.

## Auditing an existing install (the update path)

If `.claude/dprvda-kit/kit.config.json` exists: diff the installed kit files against this repo's
`template/`, list what changed upstream vs what the user hand-edited (never overwrite hand
edits), re-ask only interview answers that are stale, and apply the delta. If the config is
missing but the kit is installed (a pre-manifest install): reconstruct answers from the installed
files, confirm them with the user, and write the manifest so the next update is clean.
