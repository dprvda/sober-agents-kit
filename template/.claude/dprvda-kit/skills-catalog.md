# Skills catalog — everything validated by the 2026-07 research (967 sources) + hands-on eval

The /setup-pravda-skills interview FILTERS this catalog per project (archetype, UI, parallel
agents, overnight runs) and proposes ≤12. Descriptions follow the cold-user rule: outcomes, not
jargon. Grades: ★ = installed + tested by us hands-on · ✓ = read file-by-file · ~ = corpus-reported
(practitioner sources, not independently run). Licenses verified where graded ★/✓.

## From this kit (installed by default set, pick per project)
| Skill | What it gives you |
|---|---|
| tdd | the AI writes a test before code, so bugs are caught the moment they're made |
| systematic-debugging ★ | finds the real cause of a break instead of patching the symptom; stops and rethinks after 3 failed fixes |
| subagent-driven-dev ★ | several AI workers build parts in parallel without stepping on each other; an independent AI double-checks each part |
| receiving-code-review ★ | the AI takes criticism properly: verifies feedback before acting, never flatters |
| handoff | saves progress notes so tomorrow's session continues exactly where today's stopped |
| compact-docs | keeps project docs short enough that the AI actually reads them |
| grill-me | interrogates your plan hard before you build the wrong thing |
| to-issues | splits a plan into small tickets any session can pick up |
| zoom-out | redraws the big picture when work gets lost in details |
| audit-structure | reviews whether folders/names still make sense |
| caveman | ultra-short answers mode (saves money on long sessions) |
| write-a-skill | teach the AI a new repeatable procedure of your own |
| graphify ★ | builds a map of your whole codebase the AI can query — one question replaces reading ten files; big time and cost saver on any codebase over ~30 files |

## Third-party — vetted (license-checked; install commands in the interview)
| Pack | What it gives you | Grade / license |
|---|---|---|
| superpowers (obra) | a strict senior-engineer working style: design first, test first, verify before claiming done | ★ MIT |
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
| ashu worktree skills | gives each parallel AI worker its own ports, database, and env files | ~ |
| claude-overnight (Fornace) | overnight runs that stop at 90% of your usage window and resume cleanly | ~ |
| Ralph workflow | the simplest safe overnight loop: fresh memory each pass, hard iteration cap | ~ |
| parallel-cc / Conductor.build | detect when two AI workers are about to collide on the same code | ~ |
| getburnd / cc-cost | find where your AI spend leaks (8 known leak patterns) | ~ |

## Big collections (browse, never bulk-install — the ~12 ceiling is real)
claude-skills-collection (204 skills) · alirezarezvani/claude-skills (354, incl. security-auditor)
· awesome-claude-code-toolkit (176 plugins — CAUTION: we found 10/20 of its hooks silently broken)
· claudedirectory.org (incl. Skill Security Auditor, Ship Gate). Anything from a collection: read
SKILL.md first, pin to a commit SHA — 36% of tested community skills carried prompt injection.
