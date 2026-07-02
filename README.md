# sober-agents-kit

**One command sets up a disciplined AI-coding project: safety gates, an independent AI judge,
session memory, and a curated skill set — through a guided interview where nothing installs
blindly.**

```bash
git clone https://github.com/dprvda/sober-agents-kit && cd sober-agents-kit
claude
> /sober-setup
```

The setup interviews you (~5 minutes, every question explained in plain words, "ask me" flips any
question into a mini-interview), proposes everything from your answers, shows the full manifest of
what will land on your machine, and only then installs. Works with Claude Code fully; the commit
safety gates are git-level and protect **any** AI tool (Cursor, Codex, …).

## The story: why this kit exists

A developer who ships with AI every day described his job like this: *"I haven't written a line
of code in six months. My job now is managing six to ten occasionally drunk PhD students."*

That's the honest state of coding agents in 2026. Brilliant, fast — and occasionally one of them
guesses a leftover access token and deletes a production database **in 9 seconds, backups
included**. Another burns **$6,000 of API credits overnight** in a hook loop. Another reports
"all tests green" while every row lands in the wrong table. Real, documented incidents — not
hypotheticals.

Here's the uncomfortable finding underneath all of them: **telling the AI to behave doesn't
work.** In one documented case a MANDATORY checklist written in three different places was still
ignored twice in one session. Rules that live in prompts are advice. Rules that live in
machinery — checks that physically block a commit, a second AI that reviews the first one's
work, memory that survives restarts — actually hold.

That's this kit: **the sober adult in the room**, so you don't have to be.

It wasn't guessed together. It's built on two published studies — one on how expert operators
actually run coding agents ([967 sources](https://pravda.systems/blog/run-parallel-ai-coding-agents-without-babysitting)),
one on which platforms and tools agents can genuinely drive ([971 sources](https://pravda.systems/blog/agent-native-stack-what-to-standardize-on)) —
plus hands-on installs of every major community pack (several of which turned out to have
silently broken hooks; the survivors are in [the catalog](template/.claude/dprvda-kit/skills-catalog.md)).
Every gate in this kit maps to a real incident from that research. Every recommendation carries
its receipt.

## The setup, step by step (what you'll actually see)

| | |
|---|---|
| **1 · Start.** One command; the tool question decides the shape (AGENTS.md as the one canonical rules file, drafted in Andrej Karpathy's short-rules style). | ![step 1](docs/images/setup-1-start.png) |
| **2 · Goal.** Describe what you're building in plain sentences — the kit classifies it, drafts your never-violate rules, you confirm. | ![step 2](docs/images/setup-2-goal.png) |
| **3 · Stack.** The kit leads with the agent-native default for your kind of project — take it, name your own, or decide later. | ![step 3](docs/images/setup-3-stack.png) |
| **4 · Session memory (opt-in).** For long projects: docs the AI auto-reads every session, live progress notes, and a handoff-time check that keeps docs from lying. The AI maintains it, not you. | ![step 4](docs/images/setup-4-memory.png) |
| **5 · The AI judge (opt-in).** A second, independent AI reviews every commit — free provider available; your key never passes through chat. | ![step 5](docs/images/setup-5-judge.png) |
| **6 · Details.** Commit labels derived from your folders, integrations opt-in, parallel-work rules configured from one question. | ![step 6](docs/images/setup-6-details.png) |
| **7 · Skills.** The workflows your AI masters — proposed from your answers, filtered from a 33-entry researched catalog, every line in plain words. | ![step 7](docs/images/setup-7-skills.png) |
| **8 · The manifest.** EVERYTHING that will land on your machine — kit files vs external fetches, origins, licenses, install locations — before anything executes. | ![step 8](docs/images/setup-8-install.png) |
| **9 · Done.** A personalized CHEATSHEET.md: how to work here, day one. | ![step 9](docs/images/setup-9-done.png) |

Interactive version: open [`docs/setup-flow-demo.html`](docs/setup-flow-demo.html) in a browser.

Prefer the non-interactive path? `python install.py --target /path/to/repo [--python|--rust]` does
the copying without the interview (see [INSTALL.md](INSTALL.md)); you then fill the placeholders by
hand.

## Why

Left alone, an autonomous coding session will eventually force-push under pressure, `--no-verify`
past a failing hook, let docs drift, or re-introduce a removed code path. This kit turns "what an AI
*thinks* it should do" into "what the repo *allows*" — each gate targets a specific real failure mode.

## What's inside

Everything the kit installs lives under a single namespaced folder, **`.claude/dprvda-kit/`**, so it
can't collide with another kit a collaborator might also use. Only files that external tools *require*
at the repo root (`CLAUDE.md`, `.pre-commit-config.yaml`, …) sit at the root.

```
your-repo/
├─ AGENTS.md                 # THE standing rules — one canonical file, read natively
│                            #   by Cursor / Codex / any AGENTS.md-aware tool   [ALL TOOLS]
├─ CLAUDE.md                 # one-line bridge importing AGENTS.md for Claude   [Claude Code]
├─ .pre-commit-config.yaml   # the safety gates — run on `git commit`, so they
│                            #   protect you with ANY tool, or no tool at all   [ALL TOOLS]
├─ .gitmessage  .mcp.json  .env.example  README-CLAUDE.md (the full manual)
└─ .claude/
   ├─ settings.json          # wires the live hooks below                       [Claude Code]
   ├─ skills/                # /sober-setup /tdd /handoff /graphify …           [Claude Code]
   └─ dprvda-kit/            # all kit machinery, namespaced (renamable at install)
      ├─ gates/              # pre-commit gates + the AI judge + its prompts    [ALL TOOLS]
      ├─ hooks/              # live in-session guards (git-safety, re-inject)   [Claude Code]
      ├─ frameworks/         # verified 2026-07 fact-sheets about your tools    [ALL TOOLS]
      ├─ stack-guides/  skills-catalog.md
      ├─ inject_context_docs.py   # session memory: docs auto-load at start     [Claude Code]
      └─ docs/               # context-framework.md, parallel-agents.md
```

**The honest split:** everything that runs on git (the gates, the AI judge, the doc-freshness
checks) protects any workflow — Cursor, Codex, or a human typing alone. The LIVE layer (hooks
that block mid-session, skills, automatic session memory) is Claude Code today, because that's
where the hook API lives; ports to other harnesses are welcome, and AGENTS.md means your rules
already travel.

### The three layers
1. **Claude Code hooks** (`.claude/dprvda-kit/hooks/`) — physically block dangerous git ops, run the
   AI judge before a script launches, re-inject `CLAUDE.md` rules on every commit.
2. **Pre-commit gates** (`.claude/dprvda-kit/gates/`) — `check_file_reason`, `check_links`,
   `check_doc_freshness`, `check_md_size`, `check_secrets`, and the optional `critic_llm` AI judge,
   run by a 2-phase dispatcher. A self-defending canary protects the doc-freshness gate.
3. **Conventions** (`CLAUDE.md` + the skills) — short rules file refreshed every commit, plus
   reusable multi-step workflows.

### Optional modules (skip with installer flags)
- **AI judge** — `critic_llm` reviews each staged file via an OpenAI-compatible API (defaults to
  DeepSeek). Key via a plain `.env` (`LLM_JUDGE_API_KEY`); **blank key ⇒ it soft-passes**, so it's
  safe to leave off.
- **MCP** — `.mcp.json` for serena (code intel) + GitHub, with soft "use the MCP tool" nudges.
- **Language packs** — `packs/rust/` (cargo-audit, cargo-vet, binary-secrets), `packs/python/` (ruff).

### Seeds (`seeds/`)
Copy-paste starting points for your **global** `~/.claude/CLAUDE.md`: universal discipline rules, a
user-profile template, portable engineering lessons (Windows/git-bash/WSL gotchas, git-commit
discipline, agent-orchestration rules).

## Quick start

**Into an existing repo:**
```sh
git clone <this-repo> sober-agents-kit
cd sober-agents-kit
python install.py --target /path/to/your-repo --rust          # or: ./install.sh / .\install.ps1
```

**As a GitHub template** (new repo):
```sh
gh repo create my-new-repo --template <owner>/sober-agents-kit
cd my-new-repo
python install.py --here
```

Then fill in the `<!-- FILL IN -->` sections of `CLAUDE.md`, optionally put `LLM_JUDGE_API_KEY` in
`.env`, and open the repo in Claude Code. Full options, key setup, and troubleshooting:
[`INSTALL.md`](INSTALL.md).

## Customizing
- **Judge prompts** are plain markdown in `.claude/dprvda-kit/gates/prompts/` — edit freely.
- **Gate tiers / exempt dirs / commit scopes** are constants at the top of each gate — edit to taste.
- **Rename the kit** (`--kit-name`) if you want a different namespace; the installer rewrites refs.
