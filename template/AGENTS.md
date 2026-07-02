# __PROJECT_NAME__ — agent rules

The ONE instruction file, read natively by Codex / Cursor / OpenClaw / Hermes and imported by
Claude Code via the one-line CLAUDE.md. Rules only. Machinery lives in [`.agent-kit/`](.agent-kit/),
its mechanics in [`.agent-kit/gates/README.md`](.agent-kit/gates/README.md). Keep this file short:
past ~150 lines, agents start ignoring lines.

<!-- FILL IN: one or two sentences on what this project IS, so a fresh session is oriented. -->

## 0. First action, every session

Run `python .agent-kit/session/inject_context_docs.py --all` and read it before anything else:
the project spine (key docs, live progress, recent state). Claude Code does this automatically;
every other agent does it as this file's first instruction.

## 1. Think before coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State assumptions. Multiple interpretations? Present them, don't pick silently.
- A simpler approach exists? Say so. Push back when warranted.
- Unclear? Stop. Name what's confusing. Ask.

## 2. Simplicity first

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond the ask. No abstractions for single-use code. No unrequested configurability.
- 200 lines that could be 50? Rewrite.

## 3. Surgical changes

**Touch only what you must. Clean up only your own mess.**

- Don't "improve" adjacent code or refactor what isn't broken. Match existing style.
- Remove what YOUR change orphaned. Leave pre-existing dead code (mention it).

## 4. Goal-driven execution

**Define success criteria, then loop until verified.**

- "Add validation" → "write tests for invalid inputs, make them pass."
- After a fix: confirm with a real run, never "this should work."

## 5. The gates are law

**Every commit passes the gates. A gate failure means fix the cause.**

- NEVER `--no-verify`, never disable a test, never `assert True`, never swallow an exception.
- The AI judge may prepend `=== LLM_REVIEW_BLOCK ===` to a file: fix the listed lines, then
  remove the block ([protocol](.agent-kit/gates/README.md)).
- Force-push and remote branch deletion are blocked at the push stage, for everyone.

## 6. Never-violate project rules

<!-- FILL IN: the 2-4 domain rules a session must not break, e.g. "never touch prod data",
     "X is the only source of truth for Y". Delete this comment once filled. -->

## Pointers, not prose

- Skills (saved procedures, cross-tool SKILL.md): [`.agents/skills/`](.agents/skills/) — invoke by name.
- Commit style: `.gitmessage` (Conventional Commits; the commit-msg gate enforces it).
- `archive/` is out of context: don't read it unless named. Deadlines are deadlines, not scopes;
  never auto-pause a long run.
<!-- claude-adapter-start -->
- Claude Code live hooks (dangerous-git blocker, judge-on-launch, soft nudges):
  [`.agent-kit/adapters/claude/README.md`](.agent-kit/adapters/claude/README.md).
<!-- claude-adapter-end -->
