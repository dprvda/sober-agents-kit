# sober-agents-kit

**One interview sets up a disciplined AI-coding project: safety gates that physically block, an
independent AI judge, session memory, and a curated skill set. Works with Claude Code, Codex,
OpenClaw, and Hermes. Nothing installs blindly.**

```bash
git clone https://github.com/dprvda/sober-agents-kit && cd sober-agents-kit
```

Then start the interview from whichever agent you use:

| Your tool | How to start the interview |
|---|---|
| **Claude Code** | `claude` → `/sober-setup` |
| **Codex** | `codex` → invoke the `sober-setup` skill (it's in `.agents/skills/`), or just say *"read setup/INTERVIEW.md and run it"* |
| **OpenClaw / Hermes / anything else** | tell your agent: *"read setup/INTERVIEW.md in this repo and run it"* |

Every entry point is a thin stub over ONE canonical playbook, [`setup/INTERVIEW.md`](setup/INTERVIEW.md),
so no tool gets a second-class or drifted version. The interview takes ~5 minutes, explains every
question in plain words ("ask me" flips any question into a mini-interview), proposes everything
from your answers, shows the full manifest of what will land on your machine, and only then installs.

## The story: why this kit exists

I built and ran a 215k-line Rust trading system solo, shipping 2,872 commits in 84 days with AI
agents doing the implementation. At that pace the failure mode is not bad code. It is the
**transition**: a context window fills, the session dies or compacts, and the next session
confidently hallucinates the state — which docs are current, what was already tried, which
invariant must never break. On a trading system, a hallucinated assumption costs real money.

So the discipline moved out of prompts and into machinery: a handoff file the next session boots
from, docs that are checked against the code they describe on every commit, an independent AI
judge that reviews what the author-AI wrote, and git-level gates with no bypass flag. That
machinery ran the trading system first (13 unskippable gates on every commit). This kit is the
same machinery, generalized.

The field data says the same thing. A developer who ships with AI daily: *"I haven't written a
line of code in six months. My job now is managing six to ten occasionally drunk PhD students."*
Brilliant, fast — and occasionally one of them guesses a leftover access token and deletes a
production database **in 9 seconds, backups included**. Another burns **$6,000 of API credits
overnight** in a hook loop. In one documented case a MANDATORY checklist written in three
different places was still ignored twice in one session. Rules that live in prompts are advice.
Rules that live in machinery hold.

That's this kit: **the sober adult in the room**, so you don't have to be.

It wasn't guessed together. It's built on two published studies — one on how expert operators
actually run coding agents ([967 sources](https://pravda.systems/blog/run-parallel-ai-coding-agents-without-babysitting)),
one on which platforms and tools agents can genuinely drive ([971 sources](https://pravda.systems/blog/agent-native-stack-what-to-standardize-on)) —
plus hands-on installs of every major community pack (several of which turned out to have
silently broken hooks; the survivors are in [the catalog](template/.agent-kit/skills-catalog.md)).
Every gate maps to a real incident from that research. Every recommendation carries its receipt.

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

## What works with which tool (the honest matrix)

Almost everything is tool-neutral by construction. The one genuinely Claude-specific piece is the
in-session hook API, and its most dangerous target (history rewrites) is covered for everyone by
a git-level pre-push block.

| Layer | Claude Code | Codex | OpenClaw | Hermes | no AI at all |
|---|---|---|---|---|---|
| Commit gates + AI judge (git-level) | ✔ | ✔ | ✔ | ✔ | ✔ |
| Force-push / branch-delete block (git pre-push) | ✔ | ✔ | ✔ | ✔ | ✔ |
| AGENTS.md canonical rules | ✔ (via CLAUDE.md import) | ✔ native | ✔ native | ✔ native | n/a |
| Skills (agentskills.io SKILL.md) | ✔ `.claude/skills/` mirror | ✔ `.agents/skills/` native | ✔ `.agents/skills/` native (or `~/.openclaw/skills/`) | ✔ `~/.hermes/skills/` | n/a |
| Session memory (`.agent-kit/session/`) | ✔ automatic (SessionStart) | ✔ via the AGENTS.md first-action instruction | ✔ same (plus its own memory) | ✔ same (plus its own memory) | n/a |
| Live in-session hooks (block mid-session, BEFORE git even runs) | ✔ | — (the git-level layer covers it) | TS plugin-hook API exists — port welcome | — (the git-level layer covers it) | n/a |

The installer takes `--tools claude,codex,openclaw,hermes` and places each layer only where it
can actually run — and tells you exactly what was skipped and why. Add `--install-user-skills`
to also copy the skills into OpenClaw's / Hermes' user-level skill dirs.

## What's inside

Everything the kit installs lives under a single namespaced folder, **`.agent-kit/`**, so it
can't collide with another kit a collaborator might also use. Only files that external tools *require*
at the repo root (`AGENTS.md`, `.pre-commit-config.yaml`, …) sit at the root.

```
your-repo/
├─ AGENTS.md                 # THE standing rules — one canonical file, read natively
│                            #   by Codex / Cursor / OpenClaw / Hermes             [ALL TOOLS]
├─ CLAUDE.md                 # one-line bridge importing AGENTS.md                 [Claude Code]
├─ .pre-commit-config.yaml   # the safety gates — run on `git commit`, so they
│                            #   protect you with ANY tool, or no tool at all     [ALL TOOLS]
├─ .gitmessage  .env.example
├─ .agent-kit/               # ALL kit machinery, tool-neutral home at the root
│  │                         #   (renamable at install: --kit-name)
│  ├─ gates/                 # pre-commit + pre-push gates, the AI judge + prompts [ALL TOOLS]
│  ├─ session/               # session memory: the spine printer every agent runs
│  │                         #   at session start                                  [ALL TOOLS]
│  ├─ frameworks/            # verified 2026-07 fact-sheets about your tools       [ALL TOOLS]
│  ├─ stack-guides/  skills-catalog.md  docs/                                      [ALL TOOLS]
│  └─ adapters/              # per-tool wiring, each fenced in its own folder
│     └─ claude/             #   the one adapter that exists today: live hooks +
│                            #   the wiring manual (ports for other tools welcome)
├─ .agents/skills/           # skills, canonical home (agentskills.io — Codex,
│                            #   OpenClaw read it natively; Hermes copies from it) [ALL TOOLS]
└─ .claude/  .mcp.json       # only if you chose claude in --tools: the two files
                             #   Claude Code requires at these exact paths
                             #   (settings wiring + a skills mirror)
```

### The gates (git-level — they protect every tool)

Run on every `git commit` by a two-phase dispatcher (`run_gates_parallel.py`), no bypass flags:

| Gate | What it blocks |
|---|---|
| `check_secrets` | secret-shaped strings (keys, tokens, private keys) in the staged diff |
| `critic_llm` (the AI judge) | a second, independent AI reviews each staged file against YOUR project rules; blank key ⇒ soft-pass |
| `critic_llm_commit` | malformed Conventional Commits + judge cross-check of message vs diff |
| `check_file_reason` | any new script with no `# REASON:` header (forces reuse-vs-create thinking) |
| `check_doc_freshness` | docs drifting from the code they describe (`tracks_dir`/`frozen_at` contracts) |
| `check_links` | broken `.md` cross-references |
| `check_md_size` | docs growing past what an AI actually reads |
| `check_force_push` | (pre-push stage) force-pushes + remote branch deletions, for EVERY tool and every clone |

A self-defending canary re-tests the doc-freshness gate whenever its own script is edited.

### Session memory (`.agent-kit/session/` — all tools)

The AI's memory is wiped between sessions; people lose the first 10-15 minutes of every session
re-explaining their own project. The session module fixes it tool-neutrally:
`inject_context_docs.py --all` prints the project spine (key docs, the live progress ledger,
recent state), and AGENTS.md's first instruction tells every agent to run it before anything
else. On Claude Code it's wired to run automatically at session start (sized to your docs at
install). Pair with the `handoff` skill: verified progress notes out, a briefed session in.

### The live hooks (the Claude Code adapter, `.agent-kit/adapters/claude/`)

`block-dangerous-git` (force-push, `reset --hard`, `branch -D` … physically blocked mid-session,
before git even runs) · `check-script-launch` (the judge reviews a script before it runs) · `session-progress` (state flushed to
disk before compaction) · soft `nudge-to-*` suggestions. Other tools don't expose a hook API, so
their protection is the git-level layer above — same rules, one stage later. Spec:
[`template/.agent-kit/adapters/claude/README.md`](template/.agent-kit/adapters/claude/README.md).

### The skills (cross-tool SKILL.md format)

| Skill | What it gives you |
|---|---|
| `sober-setup` | re-run the interview any time to audit or update the setup |
| `handoff` | saves verified progress notes so tomorrow's session continues exactly where today's stopped |
| `graphify` | my standalone code-knowledge-graph tool, bundled for convenience: builds a queryable map of the whole codebase, one question replaces reading ten files |
| `systematic-debugging` | finds the real cause instead of patching the symptom; rethinks after 3 failed fixes |
| `subagent-driven-development` | parallel AI workers with an independent AI double-checking each part |
| `receiving-code-review` | takes criticism properly: verifies feedback before acting, never flatters |
| `tdd` | a test before code, so bugs are caught the moment they're made |
| `grill-me` | interrogates your plan hard before you build the wrong thing |
| `to-issues` / `compact-docs` / `audit-structure` / `zoom-out` / `caveman` / `write-a-skill` | tickets from a plan · doc trimming · structure review · big-picture re-orient · terse mode · teach a new procedure |

The interview proposes ≤12 per project (past ~12 similar skills, agents pick the wrong one) from
[the 33-entry researched catalog](template/.agent-kit/skills-catalog.md), which also
grades the vetted third-party packs (Superpowers, Planning with Files, visual-eyes, ccusage, …).

### The framework fact-sheets

13 dated one-pagers (`template/.agent-kit/frameworks/`) on Next.js, Vercel, Neon, Stripe,
auth, email, scraping, containers, Playwright, typed Python, observability, Remotion, graphify —
the verified 2026-07 state of each tool, copied into your project so the agent stops building
from stale training data. Index with one-liners: [`INDEX.md`](template/.agent-kit/frameworks/INDEX.md).

### Optional modules

- **Language packs** — `packs/rust/` (cargo-audit, cargo-vet, binary-secrets), `packs/python/` (ruff).
- **MCP** — `.mcp.json` for serena (code intel) + GitHub, with soft "use the MCP tool" nudges (`--no-mcp` to skip).
- **Seeds** (`seeds/`) — copy-paste starting points for your global rules file: universal
  discipline rules, a user-profile template, portable engineering lessons.

## The manual path (no interview, full control)

Everything the interview does is documented and doable by hand:

```sh
python install.py --target /path/to/your-repo --tools claude,codex [--rust|--python] [--no-ai-judge] [--no-mcp]
```

then fill the `<!-- FILL IN -->` blocks in `AGENTS.md`, optionally put `LLM_JUDGE_API_KEY` in
`.env` (free NVIDIA endpoint option documented there), and tune any gate — thresholds and exempt
dirs are constants at the top of each gate script. Full flags, key setup, per-tool notes, and
troubleshooting: [`INSTALL.md`](INSTALL.md). Uninstall: `python uninstall.py --target …`
(conservative: restores backups, lists anything it won't touch).

## Customizing

- **Judge prompts** are plain markdown in `.agent-kit/gates/prompts/` — edit freely.
- **Gate tiers / exempt dirs / commit scopes** are constants at the top of each gate — edit to taste.
- **Rename the kit** (`--kit-name`) if you want a different namespace; the installer rewrites refs.

## The receipts

The two studies this kit is distilled from, both free:

- [Run parallel AI coding agents without babysitting them](https://pravda.systems/blog/run-parallel-ai-coding-agents-without-babysitting) —
  the operator playbook (967 sources): worktrees, hooks, budgets, overnight lanes, and the
  origin story of these exact gates.
- [The agent-native stack](https://pravda.systems/blog/agent-native-stack-what-to-standardize-on) —
  what to standardize on when agents do the building (971 sources): the legibility test and the
  per-archetype stacks behind `stack-guides/` and `frameworks/`.
