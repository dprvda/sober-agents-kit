# Skills catalog — everything validated by the 2026-07 research (967 sources) + hands-on eval

The /sober-setup interview FILTERS this catalog per project (archetype, UI, parallel
agents, overnight runs) and proposes ≤12. Descriptions follow the cold-user rule: outcomes, not
jargon. Grades: ★ = installed + tested by us hands-on · ✓ = read file-by-file · ~ = corpus-reported
(practitioner sources, not independently run). Licenses verified where graded ★/✓.

## From this kit (the operator's own skills — the ONLY ones bundled; third-party is always installed from its original source)
| Skill | What it gives you |
|---|---|
| tdd | the AI writes a test before code, so bugs are caught the moment they're made |
| handoff | saves progress notes so tomorrow's session continues exactly where today's stopped |
| compact-docs | keeps project docs short enough that the AI actually reads them |
| grill-me | interrogates your plan hard before you build the wrong thing |
| to-issues | splits a plan into small tickets any session can pick up |
| zoom-out | redraws the big picture when work gets lost in details |
| audit-structure | reviews whether folders/names still make sense |
| caveman | ultra-short answers mode (saves money on long sessions) |
| write-a-skill | teach the AI a new repeatable procedure of your own |

## Third-party — vetted (license-checked; install commands in the interview)
| Pack | What it gives you | Grade / license |
|---|---|---|
| graphify (safishamsi) | builds a queryable map of your whole codebase — one question replaces reading ten files; big saver past ~30 files. CLI: `uv tool install graphifyy` (PyPI); skill from github.com/safishamsi/graphify, pin a SHA | ★ (we run it daily) |
| superpowers (obra) | a strict senior-engineer working style: design first, test first, verify before claiming done. Its systematic-debugging, subagent-driven-development, and receiving-code-review skills are the three we run daily (★ hands-on). ALWAYS installed from obra's repo at setup, never bundled here | ★ MIT |
| planning-with-files | the AI keeps a written plan + findings on disk and refuses to quit mid-phase; survives restarts | ✓ MIT |
| ponytail | forces "does this code even need to exist?" before writing; measured ~54% less code | ✓ MIT |
| visual-eyes | the AI looks at screenshots of your app and fixes what looks wrong | ★ MIT |
| ccusage | shows what your AI usage really costs, from your own machine's logs | ★ MIT |
| frontend-design (Anthropic) | a real design direction so your UI doesn't look like every AI template | ✓ Apache-2.0 |
| /simplify (bundled in Claude Code) | three parallel reviewers strip needless complexity as a final pass | native |
| find-skills (vercel-labs) | searches the ecosystem for a skill matching your goal | ~ |
| web-quality set (Addy Osmani) | six checks: speed, accessibility, SEO, best practices, with hard budgets | ~ |
| DeepEval skill | measures whether your AI features actually work, with scores | ~ |
| Trail of Bits security set | professional security scanning workflows (CodeQL/Semgrep) | ~ |
| HashiCorp set | official Terraform style/test/refactor procedures | ~ |
| GitHub PR Review skill | reviews pull requests with an approval gate before anything posts | ~ |
| write-readme (solmaz) | forces defining what a tool IS, not what it does | ~ |
| Silver Platter | audits your whole Claude config into a map + 30-day plan | ~ |
| fewer-permission-prompts | scans your history and proposes safe auto-approvals | native skill |

## Parallel-work & overnight helpers (propose only when the answers call for them)
| Tool | What it gives you | Grade |
|---|---|---|
| ashu worktree skills | per-worker ports, database, and env files — ONLY for tools WITHOUT native worktrees. On Claude Code do NOT propose this: `claude --worktree` / `isolation: worktree` is native, plus the AGENTS.md worktree ritual (issue #4; the pack also had no verifiable pinned source at eval time) | ~ |
| claude-overnight (Fornace) | overnight runs that stop at 90% of your usage window and resume cleanly | ~ |
| Ralph workflow | the simplest safe overnight loop: fresh memory each pass, hard iteration cap | ~ |
| parallel-cc / Conductor.build | detect when two AI workers are about to collide on the same code | ~ |
| getburnd / cc-cost | find where your AI spend leaks (8 known leak patterns) | ~ |

## Big collections (browse, never bulk-install — the ~12 ceiling is real)
claude-skills-collection (204 skills) · alirezarezvani/claude-skills (354, incl. security-auditor)
· awesome-claude-code-toolkit (176 plugins — CAUTION: we found 10/20 of its hooks silently broken)
· claudedirectory.org (incl. Skill Security Auditor, Ship Gate). Anything from a collection: read
SKILL.md first, pin to a commit SHA — 36% of tested community skills carried prompt injection.
