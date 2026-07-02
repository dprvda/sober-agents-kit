---
name: handoff
description: Prepare a clean session handoff for the next AI session — commit + push all in-flight changes, write a structured handoff file using the PASS-AI framework (Project state / Action list / Situation awareness / Sources / AI extras), update MEMORY.md index. Use when the user signals they're about to clear context, wrap up the session, or hands off to a new session ("clearing context", "let's wrap up", "save state", "/handoff", "I'm done for now").
---

# REASON: Generalised PASS-AI session handoff skill, because the btc-specific Data-state half-step and hardcoded paths would break in any other repo; uses __PROJECT_NAME__ and repo-relative paths instead.

# Session handoff (PASS-AI framework)

## Tempo reminder for the next session (read first)

You code ~100× faster than humans. A "tomorrow" / "by morning" deadline is **dozens** of properly-done tasks, not one. Quality bar stays full per item; the multiplier is on how many items fit.

Walk the Action list top-down: hooks → commit → push → next. List empty? Walk `docs/progress/roadmap.md` → code TODOs → `docs/planning/backlog.md`. Don't invent scope; don't idle.

Stop only when: real user choice needed (scope / real-money / force-push) · hooks fail + fix needs scope creep · within ~30 min of deadline.

---

## What this is

User is about to clear context. Prepare everything the next session needs to pick up cold.

**Framework: PASS-AI** — adapted from I-PASS (medical sign-out) to agentic working-state transfer.

## The five sections (always in this order)

§1 → §2 → §3 → §4 → §5.

### 1. **P**roject state

Capture the current working-tree + repo state:

- Current branch + remote tracking + divergence (`git status`,
  `git log origin/master..HEAD --oneline`)
- Last 3-5 commits with one-line summaries
- Working-tree state (clean? files modified? files staged?)
- Any in-flight drafts / WIP commits
- Any background processes still running (dev servers, watchers, etc.)
  with PID + port + log location

### 2. **A**ction list (ordered)

Numbered, in priority order. For each item:

- What to do (concrete, single sentence)
- Why (one sentence)
- Acceptance criterion ("done when X")
- Estimated session time (10 min / 30 min / multi-hour / unknown)
- **STOP-IF checkpoint** for any item that depends on a fact
  that might have changed — e.g. "STOP if origin/master has
  moved past <commit>; pull first."

The first action should be the SINGLE MOST IMPORTANT next step.
The new session reads this list top-down and does them in order.

### 3. **S**ituation awareness

Things that would surprise the next session if they didn't know:

- Locked decisions from this session — what's now off-limits
- Hard limits (force-push to master, real-money launches, etc.)
- Recently-discovered gotchas (platform-specific workarounds, etc.)
- Open questions waiting on the user
- "Do not redo" — work that looks pending but is actually done
- Diff vs the previous handoff if the prior session left one

### 4. **S**ources (read these first)

Pointer list for cold-start AI. In recommended-read order:

- The handoff file itself
- `CLAUDE.md` (project rules — always)
- The most-recent commits' diffs (the work this session shipped)
- Specific docs touched this session

Mark each with token weight: read FULL / SKIM / GREP-ONLY. Helps
the next AI budget context.

### 5. AI-specific extras

- Recommended skills for the next session's first action
- Slash commands that might apply (`/audit-structure`, `/compact-docs`,
  etc.)
- Tools / hooks that fire automatically and what they expect
- Time estimate for the action list (sum from §2)

## Process

### 1. Check the working tree first

```bash
git status
git log origin/master..HEAD --oneline
git stash list
```

If anything is uncommitted, ask the user what to do (commit,
stash, discard) — never auto-commit work the user might not want
shipped.

### 2. Commit + push pending work

For each clean commit unit:

- Run the full pre-commit hook pipeline (NEVER `--no-verify`)
- If hooks fail, fix the listed issues + retry
- Use heredoc for commit message bodies
- Push to `origin/<current-branch>` (NOT to master from a feature
  branch unless explicitly authorised)
- For master: confirm with the user before pushing if the user
  isn't already in the loop

### 3. Write the handoff file

**Path:** `.claude/handoffs/handoff_<YYYYMMDD>_<HHMMSS>_<short_kebab_title>.md`

- Folder: `.claude/handoffs/` in the repo (git-tracked, alongside other `.claude/` infra)
- Naming: 8-digit date + 6-digit time (HHMMSS) + descriptive kebab-case stem (≤6 words)
- Time component matters because multiple handoffs in the same day must sort correctly via `ls`
- Example: `.claude/handoffs/handoff_20260429_213045_auth_refactor_done.md`

**Limit: max 5 handoffs in the folder.** When writing a new one:

1. Compose the new handoff at the planned filename.
2. List existing handoffs sorted by filename ascending (`ls .claude/handoffs/ | sort`).
3. If after add the count would exceed 5, `git rm` the oldest entries until count == 5.
4. Stage adds + removes in the same commit.
5. Commit message follows Conventional Commits: `chore(meta): handoff <YYYY-MM-DD> — <short topic>`.

Older handoffs aren't lost — they live in `git log`. Recover via `git show <sha>:.claude/handoffs/<file>.md`.

YAML frontmatter:

```yaml
---
name: Session handoff <YYYY-MM-DD> — <one-line topic>
description: <one-paragraph what this handoff covers + the new session's required entry action>
type: project
originSessionId: <current session id if known, else "unknown">
---
```

Body: the five PASS-AI sections, in order, with the conventions above.

### 4. Update MEMORY.md (in user-Claude memory, separate from repo)

# NOTE: The MEMORY.md path depends on how the user's Claude project is stored.
# Typical pattern: ~/.claude/projects/<project-slug>/memory/MEMORY.md
# Replace <project-slug> with the actual slug for this project.

The user-level memory index is **separate** from the in-repo `.claude/handoffs/` folder — MEMORY.md is durable cross-session memory; handoffs are committed state captures.

**Path-only convention.** MEMORY.md is an index, not a digest. The handoff *file* carries every byte of detail; MEMORY.md just points at it. Hard rule: each handoff entry is ONE line, **NO inline summary**, **NO track tag**, **NO "READ FIRST"** — just the link. The next session opens the file; the file owns the content.

Steps:

1. **Delete the existing handoff entry** in `### Active` (the line that starts with `- [.claude/handoffs/handoff_`). Do **not** move it to a "Prior" section. Git history of `.claude/handoffs/` and `git log` already preserve order.
2. Prepend the new entry to `### Active`, **path-only**:

```markdown
- [.claude/handoffs/handoff_<YYYYMMDD>_<HHMMSS>_<topic>.md](.claude/handoffs/handoff_<YYYYMMDD>_<HHMMSS>_<topic>.md)
```

That's the entire entry. No prose after the link. Use a repo-relative path (not a GitHub URL) — shorter, and the next session can `cat` it directly.

3. If MEMORY.md ever exceeds 20 KB total, stop and audit before adding anything new — something else has accreted that shouldn't be in an index.

### 5. Surface the handoff in the user's session output

Before ending, print to chat:

- The handoff file path
- The TL;DR (first paragraph)
- The Action #1 from the handoff
- Confirmation that all pending commits + pushes happened (or
  explicit list of what didn't)
- Reminder: "next session — read CLAUDE.md + this handoff first"

### 6. Don't end the session yourself

Never run `/clear` or anything that wipes context. The handoff is
the LAST thing this session does — the user clears context.

## What NOT to do

- Don't `--no-verify` any commits, ever. If hooks fail, fix and retry.
- Don't auto-push to master from a feature branch.
- Don't write the handoff file before committing — handoff
  should describe a CLEAN tree, not a messy one.
- Don't fabricate "what's done" — only list things actually
  pushed / committed / verified.
- Don't write a 5000-word handoff for a 30-minute session. Match
  length to scope.
- Don't include time-sensitive info that'll rot ("at 18:35 today...");
  use absolute dates only.
- Don't skip the "diff vs previous handoff" check — drift across
  sessions is the framework's whole point.

## Frequency / when this fires

- User explicitly says "I'm wrapping up", "clearing context",
  "let's hand off", "save state", "/handoff"
- User says "we're done" + scope was a multi-step session
- AI detects context budget approaching limit AND has multi-step
  work in flight — proactively offer to handoff
- NOT for one-shot answers / trivial sessions

## Related

- `.claude/commands/handoff.md` — slash-command wrapper
- MEMORY.md (see path note in §4 above) — the index this updates
- Past handoffs in `.claude/handoffs/` — examples to match style
- `CLAUDE.md` "Documentation discipline" — the rules the handoff itself documents

## The continuity ledger (maintain DURING work, not at the end)

A handoff written from memory at session end is the amnesia pattern — anything since the last
save is gone after a crash or compaction. The fix (validated across the 2026 operator research):

1. **Maintain `.claude/session-progress.md` WHILE working**: append after every completed step
   and after every ~2 research/exploration actions. Fields: current state (branch, running
   processes, exact next command) · what was done (file paths) · what FAILED and why (the most
   valuable field) · key decisions verbatim.
2. **The PreCompact hook** (`hooks/session-progress.py`) forces a flush before compaction; the
   SessionStart injector loads the ledger FIRST in a fresh session.
3. **/handoff becomes a FINALIZE step, not a memory dump**: read the ledger, VERIFY its claims
   against `git log`/`git diff` (a claim the diff doesn't support gets corrected, not copied),
   write the PASS-AI handoff from the verified ledger, then reset the ledger for the next session.
