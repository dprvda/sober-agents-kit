# The sober-setup interview — the ONE canonical playbook (every tool runs this file)

You are an AI agent, and you are about to set up (or audit) a project's AI-coding discipline
layer. This file is the complete script. It is tool-neutral on purpose: the same interview runs
whether you are Claude Code, Codex, OpenClaw, Hermes, or any agent that can read a file, ask
questions, and run `python install.py`. The per-tool entry stubs (`.claude/skills/sober-setup/`,
`.agents/skills/sober-setup/`) all point here; nothing is duplicated.

The kit's machinery lives in this repo under `template/`; `install.py` copies it. Your job is
everything `install.py` cannot do: ask the right questions, derive the right configuration, write
the per-project pieces by hand, and leave the user with a cheatsheet instead of a README maze.

**The one rule that shapes every answer** (from the 2026 operator research): *a gate enforces, a
skill teaches, a subagent isolates, the rules file routes.* Anything correctness-critical goes in
an enforced gate (even triple-documented advisory rules get ignored). Anything the user retypes
goes in a skill. Keep the installed skill count ≤ ~12: at ~20 similar skills agents pick the
wrong one, and in one field test 40 of 47 installed skills made output worse.

## Stage 0 — know your tool, read the current facts

**STEP ZERO A — WHICH AGENT ARE YOU?** Identify the harness you are running in (Claude Code /
Codex / OpenClaw / Hermes / other). It decides which layers you can wire (the matrix below) and
how you ask questions: use your structured multiple-choice question tool if you have one
(Claude Code: AskUserQuestion); otherwise ask the same questions as plain numbered chat messages,
one batch at a time.

**STEP ZERO B — READ BEFORE ANYTHING (your training data is stale):** read
`template/.claude/dprvda-kit/frameworks/INDEX.md` and the framework files matching any stack
under discussion, plus `template/.claude/dprvda-kit/skills-catalog.md` and the relevant
`template/.claude/dprvda-kit/stack-guides/*.md`. These carry the verified 2026-07 state of every
tool (breaking changes, official AI connections, real incidents) from a 971-source study — the
tools shipped breaking changes AFTER your training. You advise the user FROM these files, never
from memory.

**THE PER-TOOL MATRIX (verified 2026-07 — what each harness can actually run):**

| Layer | Claude Code | Codex | OpenClaw | Hermes | any other |
|---|---|---|---|---|---|
| Commit gates (pre-commit, git-level) | yes | yes | yes | yes | yes — they run on `git commit`, no AI tool involved |
| AGENTS.md canonical rules | yes (via the one-line CLAUDE.md import) | yes (native) | yes (native, workspace) | yes (native, also reads CLAUDE.md) | if it reads AGENTS.md |
| Skills (SKILL.md folders) | yes — `.claude/skills/` | yes — `<repo>/.agents/skills/` or `~/.agents/skills/` (agentskills.io format) | yes — `<workspace>/skills/` or `~/.openclaw/skills/` (agentskills.io format) | yes — `~/.hermes/skills/` (agentskills.io format) | if it supports agentskills.io |
| Live in-session hooks (block a dangerous command BEFORE it runs) | yes — shell hooks in `.claude/settings.json` | no | possible via its TypeScript plugin-hook API — the kit does not ship one yet (port welcome) | no documented hook API | no |
| Session memory (docs auto-load each session + progress ledger) | yes — SessionStart/PreCompact hooks | no (docs still help: point AGENTS.md at them) | partial — OpenClaw has its own MEMORY.md system; the kit's docs convention still works as readable files | partial — same, Hermes has its own memory | no |

Be honest about this split at every step: the git-level gates protect the user with ANY tool or
no tool; the live layer is Claude Code today. Never imply a layer works where it does not.

## Stage 1 — the interview (two batches)

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
one-line WHY, one example answer, and the standing offer: "unsure? say ASK ME and I will
interview you for this one question — short follow-ups until we have the answer — or just answer
roughly and I refine it." A vague answer is never rejected: draft the refined version yourself
(e.g. turn a loose project description into candidate never-violate rules) and present it for
confirmation. Nothing is final until the pre-install SUMMARY, where every derived decision is
shown once and the user can amend any line before anything is written.

Batch A (the project):
1. **What are you building? A few plain sentences: what it does and the goal.** ONE question,
   two jobs: (a) DERIVE the archetype yourself (SaaS web app / data pipeline / content-video
   pipeline / API service / other) and confirm it in one line ("sounds like a data pipeline —
   correct me if not") — never ask the user to classify; (b) the text becomes the tailoring
   source: frame the WHY as "this answer shapes the whole setup — rules, checks, and system
   prompts get tailored to what you build" (no internal jargon). The confirmed archetype drives
   the OPTIONAL stack-guide injection (`stack-guides/<archetype>.md` → `docs/STACK.md`, an
   AGENTS.md pointer line; "other" or deferred → note as pending in kit.config.json, activatable
   by re-running). Internally the text feeds the judge's `project-context.md` + the AGENTS.md
   fill-in.
2. **What are the 2-4 rules that must NEVER be violated here?** (Money movement? Data deletion?
   A public API? These become judge context + candidate live-hook blocks where the tool has hooks.)
3. **Stack — LEAD WITH THE PROPOSAL. By this point you know the archetype; never open with a
   quiz.** (a) EXISTING repo: detect from the files (package.json, pyproject.toml, Cargo.toml),
   confirm in one line, skip the rest. (b) NEW project: immediately present the agent-native
   default for the derived archetype from `stack-guides/` (the verified 2026 selection rule: pick
   tools by agent legibility — full API + key auth + official MCP + machine docs — e.g. a data
   pipeline gets typed Python + a container host + Neon; a SaaS app gets TypeScript/Next + Vercel
   + Neon + Stripe), one-sentence why per pick, then exactly three options: take it / name your
   own / decide later. WHEN THE STACK IS CONFIRMED: copy each chosen framework's doc from
   `frameworks/` into the target as `docs/framework-<name>.md` (keep the frozen_at stamp). Tell
   the user why in plain words: "I'm also copying short, current fact-sheets about each tool you
   picked into your project — AIs are trained on older versions, and these files travel with the
   project, so your AI always knows the CURRENT way to use your tools." List them in the Stage-2
   manifest. Offer the deep-dive link for the curious: the full reasoning and per-archetype
   tables live at pravda.systems/blog/agent-native-stack-what-to-standardize-on. THE GUIDE IS
   OPTIONAL: if the stack is known/proposed, inject `docs/STACK.md` (stack + how an AI agent must
   behave on it); if the user wants to decide later, skip it and note in kit.config.json that the
   guide is pending — re-running the interview activates it any time. Nothing else in the setup
   depends on it.
4. **Will multiple AI sessions/agents work here in parallel?** (If yes: recommend one isolated
   working copy per stream — in Claude Code that is native `claude --worktree`, elsewhere plain
   `git worktree add` — port/DB isolation notes in AGENTS.md, and NO per-commit tagging — the kit
   removed its Tag-trailer hook because tags race in shared `.git` under parallel agents.)

Batch B (the machinery):
4a. **Docs & session memory — ASK, don't assume. Explain it as the STORY, not a feature list:**
   "Here's a problem nobody tells you about: the AI's memory is completely wiped between
   sessions. Tomorrow it remembers nothing — people lose 10-15 minutes of every session
   re-explaining their own project, every single day. The fix has two parts.
   Part 1: the project's knowledge lives in a few short docs, and the AI reads them before doing
   anything — like an employee who reads the team wiki before starting the day. You never
   re-explain; it just knows. (In Claude Code this loading is automatic every session; in other
   tools AGENTS.md points at the docs and the agent reads them on demand.)
   Part 2: docs lie over time. Code changes, the doc describing it doesn't, and then the AI
   trusts a wrong doc and confidently breaks things. So every doc declares what it describes,
   and at every session HANDOFF (the wrap-up commit) an automatic check compares them: if the
   code changed but its doc didn't, the wrap-up is held until the doc is fixed. AND THE AI FIXES
   IT — not you. Your entire job is, once in a while, answering 'update the doc or acknowledge
   the drift?' when asked. This is what makes a months-long project possible. A weekend script
   doesn't need it."
   Then offer: FULL (reading + progress notes + the doc-check) / MEMORY-ONLY (reading + progress
   notes, no doc-check) / OFF (activatable later by re-running). Record in kit.config.json.
4b. **Which AI coding tool(s)?** Claude Code / Codex / OpenClaw / Hermes / Cursor / several.
   Explain the split honestly per the Stage-0 matrix: the COMMIT GATES are git-level and protect
   you with ANY tool (they run on git commit, not inside the AI); live blocking hooks and
   automatic session loading are Claude Code features today. Whatever the mix, write AGENTS.md
   as the canonical instruction file (Codex, Cursor, OpenClaw and Hermes all read it natively)
   with CLAUDE.md as a one-line @AGENTS.md import bridge. Pass the chosen set to the installer as
   `--tools` (e.g. `--tools claude,codex`); it places skills where each tool looks (Claude:
   `.claude/skills/`; Codex + OpenClaw project-level: `.agents/skills/`) and prints the exact
   copy command for the user-level dirs it never touches (OpenClaw `~/.openclaw/skills/`, Hermes
   `~/.hermes/skills/`). Say exactly what was skipped for non-Claude tools and why.
   THEN explain the instruction files themselves in cold words: "AGENTS.md is the AI's standing
   instructions — the rules it reads every single session, whichever tool you open. The kit keeps
   it under ~200 lines because past that AIs start ignoring lines; must-never rules go into
   enforced gates instead, procedures go into skills, and this file just routes." Then PROPOSE
   the starting content in Andrej Karpathy's style — say his name, it earns trust — a short
   numbered list of judgment rules drafted from THEIR answers (Karpathy's own rules file
   reportedly cut his AI's mistake rate from 11% to 3%): "if code can answer, code answers" ·
   fail loud, never silently · read before you write · plus their own never-violate rules from
   question 2. Show the drafted file, then ask: keep this style, make it even more minimal, or
   write your own structure?
5. **Enforcement level** — Strict (all gates, judge blocking) / Standard (gates + judge
   soft-advisory) / Light (secrets + dangerous-git only). Map to install flags + gate roster.
6. **The AI judge — ASK as a want-this question:** "Do you want a separate AI judge — a second,
   independent AI that reviews every commit before it lands? The AI that wrote the code is a bad
   judge of its own work (it rubber-stamps itself); a different model catches what the author
   misses, using your never-violate rules as its checklist. It runs at the git level, so it
   protects every tool you use." Options: yes-free (NVIDIA) / yes-own provider / no judge
   (addable later). Provider details — NVIDIA build endpoint (FREE, recommended: one `nvapi-` key
   at https://build.nvidia.com, `LLM_JUDGE_BASE_URL=https://integrate.api.nvidia.com`,
   `LLM_JUDGE_MODEL=mistralai/mistral-medium-3.5-128b`) / any OpenAI-compatible host they
   already pay for / none (`--no-ai-judge`).
7. **Commit scopes** — propose a list derived from the repo's top-level folders (e.g.
   `core|api|ui|docs|build|ci|deps|meta`), let them edit. Patch `ALLOWED_SCOPES` in
   `critic_llm_commit.py` with the result.
8. **Skills to activate — a FIRST-CLASS choice, explained like the stack, never "extras".**
   Open by explaining what a skill IS in user language: saved expert procedures the AI applies on
   its own (how to test, how to debug, how to run parallel work) — they shape the QUALITY of
   everything built here, and the SKILL.md format is a cross-tool standard (agentskills.io) that
   Claude Code, Codex, OpenClaw and Hermes all read. Then PROPOSE a set FILTERED FROM
   `skills-catalog.md` — the full catalog of everything the 2026-07 research (967 sources) +
   hands-on eval validated (kit skills, vetted third-party, parallel/overnight helpers,
   collections). Always tell the user the filter math ("proposing 8 of 33 — the rest didn't fit
   this project; full catalog: skills-catalog.md; the full study behind the menu:
   pravda.systems/blog/run-parallel-ai-coding-agents-without-babysitting"). Under the ~12 ceiling
   (past ~12 similar skills agents pick the wrong one). Kit skills matched to the archetype and
   answers (e.g. data pipeline + parallel agents → tdd, systematic-debugging,
   subagent-driven-development, handoff, compact-docs; UI work → add visual-eyes; unsure
   planning → grill-me), plus the vetted third-party menu (Stage 3) folded in as unchecked extras
   with license + cost notes. The user confirms/edits one checklist; deselected skills are listed
   in the cheatsheet as add-when-needed.
9. **MCP servers** — GitHub? Serena (code navigation)? Neither (`--no-mcp`)? If Serena: ask which
   dirs hold code and patch `CODE_DIR_PREFIXES` in `nudge-to-serena.py`. (MCP wiring ships for
   Claude Code's `.mcp.json`; Codex/OpenClaw/Hermes have their own MCP config surfaces — offer
   the server list and let their native config carry it.)

## Stage 2 — install + configure

**THE MANIFEST GATE (binding): nothing installs blindly.** Before ANY write or fetch, present the
COMPLETE manifest and get explicit confirmation: every file that will be written into their
project (grouped, with one-line purposes); every EXTERNAL fetch separately, each with its source
repo URL, license, install location (project vs user-level vs global npm), and why it's needed;
and the closing line "nothing else — no telemetry, no network calls except the judge API you
configured; every file is readable text." Deselected externals are listed as NOT-now with their
future install command.

1. Run `python install.py --target <path> --project-name <name> --tools <list> [flags from the
   interview]`.
2. Write `gates/prompts/project-context.md` from answers 1+2 (the judge appends it to its rubric
   automatically).
3. Fill the two `<!-- FILL IN -->` blocks in the target's `AGENTS.md` from answers 1+2.
4. Patch `ALLOWED_SCOPES` (answer 7) and `CODE_DIR_PREFIXES` (answer 9) where applicable.
5. Write the target's `.env` as a PREFILLED TEMPLATE (from `.env.example`): base URL + model
   filled for the chosen provider, `LLM_JUDGE_API_KEY=` left blank. NEVER ask the user to paste a
   secret into the chat. Tell them exactly where to get the key, which file to open, and that
   everything soft-passes until it's filled; give the self-test command to verify afterwards.
6. Write `.claude/dprvda-kit/kit.config.json`: every interview answer (including the tool list) +
   the kit commit SHA + timestamp. This is the update manifest — a future re-run reads it,
   re-asks only what changed, and can re-derive every generated file without clobbering hand
   edits.
7. EVERY doc this setup writes gets its freshness stamp: `docs/STACK.md` and `CHEATSHEET.md`
   carry `frozen_at: <install date>` frontmatter (the doc gate blocks unstamped docs). Explain
   the system to the user in plain words: "project docs carry a freshness contract — either 'this
   snapshot is dated' (frozen_at) or 'this doc must change when these folders change'
   (tracks_dir); a check on every commit keeps docs from silently rotting." On Claude Code, also
   tell them the payoff: anything in docs/ is auto-loaded into every fresh session (the
   SessionStart injection), so STACK.md's best practices follow the AI everywhere without
   re-explaining; complete the session-system walk: "every fresh session auto-loads your project
   docs + the live progress ledger, so the AI never starts blind; while working it keeps notes in
   .claude/session-progress.md, and /handoff turns those verified notes into a baton for the next
   session." On other tools, the same docs work as read-on-demand files AGENTS.md points at.
   Usage example in the cheatsheet: 'new session → it already knows the state; end of day → run
   /handoff (or tell the agent: run the handoff skill)'.
8. If parallel agents = yes: append the worktree ritual to AGENTS.md (one worktree per stream;
   contracts/migrations/lockfiles stay main-session-only; merges sequential).
9. Per-tool finish (from the Stage-0 matrix): for OpenClaw/Hermes, print the one copy command
   that puts the chosen skills into their user-level skills dir, and remind that OpenClaw's
   frontmatter parser wants single-line YAML values. For every non-Claude tool, confirm AGENTS.md
   is in the place that tool reads (repo root for Codex/Cursor; the workspace for OpenClaw).

## Stage 3 — propose third-party packs (links + commands only, never vendor them)

Present as a menu, install only what they pick, and warn: *Snyk found prompt injection in 36% of
tested community skills — read SKILL.md before installing, pin to a commit SHA.* Respect the
~12-skill ceiling: adding a pack usually means NOT adding another.

| Pack | What it earns | Install |
|---|---|---|
| Superpowers (obra) | full spec→TDD→subagent-review methodology | `claude plugins:install superpowers` (check its license page first) |
| Planning with Files | plan-first + save-findings-every-2-actions + session recovery | via `npx skills add` / its repo README |
| Anthropic Frontend Design | escape "Inter font, purple gradient" defaults | plugin marketplace |
| visual-eyes | Playwright screenshots so the AI sees its own UI | its repo README |
| ccusage | offline cost reports from local JSONL, zero API calls | `npm install -g ccusage` |

## Stage 4 — emit the cheatsheet

Write `CHEATSHEET.md` at the target root, personalized by the answers AND the tool list. Contents
(adapt, don't copy blindly): the four-phase loop (explore/plan first → implement → commit; skip
planning only when the diff fits one sentence); the placement rule (gate enforces / skill teaches
/ rules file routes); the worktree commands (if parallel); the cost levers for their tool (on
Claude Code: `CLAUDE_CODE_SUBAGENT_MODEL=haiku`, `--max-budget-usd` on every headless run,
`.claudeignore`, `/usage` weekly); the escape hatches (`--ack-no-drift`, `# SECRET_OK:`,
`# REASON:`); what each installed gate blocks and how to fix (never bypass); which layers are
live for which of their tools (the honest matrix row); and the judge's provider + how to rotate
its key.

## Auditing an existing install (the update path)

If `.claude/dprvda-kit/kit.config.json` exists: diff the installed kit files against this repo's
`template/`, list what changed upstream vs what the user hand-edited (never overwrite hand
edits), re-ask only interview answers that are stale, and apply the delta. If the config is
missing but the kit is installed (a pre-manifest install): reconstruct answers from the installed
files, confirm them with the user, and write the manifest so the next update is clean.
