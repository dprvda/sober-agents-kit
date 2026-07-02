---
title: Parallel sub-agent workflow — what works, what fights the toolchain
description: How to run multiple sub-agents in parallel on __PROJECT_NAME__ without race-induced workloss. Captures the friction modes — pre-commit-gate worktree scans, merge-commit subject blocks, and cwd drift (the single most dangerous one) — and the workflow that avoids them — agents write + test in isolated worktrees but DO NOT commit; the orchestrator collects diffs via git -C (never cd-ing into a worktree) and commits serially in main.
frozen_at: 2026-06-02
---

# Parallel sub-agent workflow

## Why this doc exists

Multi-agent batches dispatched with `isolation: "worktree"` Agent calls surface several friction modes that are not obvious until encountered. Three classes of problem repeatedly appear: pre-commit gate walkers that scan agent worktrees, merge-commit subjects that fail Conventional Commits gates, and cwd drift. This doc captures what we learned so the next batch ships cleanly.

## What works

### Worktree isolation per agent

Each agent runs in `.claude/worktrees/agent-<id>/` — a real git
worktree linked to the main `.git/`. Files written by agent A are
invisible to agent B; each agent's `git status` / `git diff` reflects
only its own changes. No stash-race wipes between agents.

### Parallel research / read-only investigation

Multiple agents querying the codebase to investigate a divergence
return coherent independent findings in a fraction of the wall-clock
time of sequential work. No shared-state issues because nothing
commits.

### Cleanly-disjoint code touches

When the file-touch matrix is genuinely disjoint, each agent's work
is a clean diff. Zero cross-overlap means each patch applies without
conflict.

## What fights the toolchain

### Pre-commit gates scan agent-worktree files

File-walking gates (e.g. `check_file_reason.py`) walk the filesystem
under `REPO_ROOT` via `os.walk`. The agent worktrees live at
`.claude/worktrees/agent-*/` *inside* the main checkout. When the
main shell commits, the gates walk every agent's full source tree and
inflate the file count dramatically. Fix: add `worktrees` to each
gate's `EXEMPT_DIR_PARTS` (or equivalent exclusion list).

### Merge commits need Conventional Commits subjects

The default `Merge branch 'origin/worktree-agent-...'` subject fails
the commit-msg gate. Every merge requires a hand-crafted
`<type>(<scope>): #N merge ...` line. Cherry-picking the agent's
commit (`git cherry-pick <sha>` then `git commit -C` to re-author)
sidesteps this — the original commit subject was already CC-formed.

### Push races on shared `.git/`

When two agent worktrees both `git push --follow-tags` to the same
remote, the ref-update is serialized by GitHub but local post-commit
tag hooks can race on `.git/refs/tags/`. Mostly invisible but adds
friction — sometimes one push reports a tag-already-exists rejection
even when the tag belongs to the OTHER agent's branch.

### cwd drift — the single most dangerous failure mode (read this twice)

The `Bash` tool's working directory **persists across calls**. One
`cd` into a worktree — or anywhere — sticks silently until the next
`cd`; every command in between inherits it.

Why that is dangerous: once the cwd has drifted, **every relative-path
command silently operates on the wrong tree, with no error and
plausible-looking output** — `git status`, `git diff`, `git add`,
`git commit`, `git apply`, `ls`, file-size checks. Nothing
warns you. **The harness has no cwd-drift detector** — there is no
automatic check, no alarm; this is 100 % self-enforced discipline, not
a best-effort. Treat the rules below as hard rules.

Two real incidents this failure mode has caused:

- **Wayward commit.** The orchestrator `cd`'d into an agent worktree
  to read a diff, then `git add` + `git commit`. The commit landed on
  the worktree branch, NOT main. `git push origin main` reported
  "Everything up-to-date" — main was genuinely unchanged. Work was
  lost on the wrong branch.
- **False data-loss alarm.** A session's `Bash` cwd had persisted into
  a worktree checkout. Every relative-path diagnostic that followed
  read the *worktree's* tree, not main's; the session concluded that
  turns of work were lost. They were not — the work was intact in main
  the whole time. cwd drift, not data loss, was the only bug.

**The discipline — apply every time, no exceptions:**

1. **NEVER `cd` into a worktree.** To inspect an agent's worktree use
   `git -C "<abs-worktree-path>" <cmd>` — it acts on that worktree
   *without moving the shell's cwd*. To read its files use the `Read`
   tool with an absolute path. There is no reason to ever `cd` into
   `.claude/worktrees/`.
2. **Lead every git-touching `Bash` command with an absolute
   `cd "<main-checkout-abs-path>" && …`.** An absolute `cd` *resets*
   the cwd to the main checkout regardless of prior drift, so that one
   command is drift-proof. This is the de-facto guard — it makes the
   command correct, but it is a per-command *reset*, NOT a detector;
   it does not tell you drift happened, it just neutralises it.
3. **Prefer the dedicated tools.** `Read` / `Glob` / `Grep` take
   absolute paths and are immune to cwd entirely — use them over
   `cat` / `find` / `ls`.
4. **A surprising `git status` / `ls` / size result is cwd drift
   until proven otherwise.** Before believing ANY alarming
   relative-path observation, run `pwd` + `git rev-parse
   --show-toplevel` and confirm both equal the main checkout. Drift is
   far more likely than real corruption — check the cheap explanation
   first, every time.

Recovery from a wayward commit: `cd` back to the main checkout,
re-stage + re-commit on main, delete the orphan tag locally
(`git tag -d <tag>`), and flag the orphan branch for operator cleanup
at session-wrap.

## The locked workflow

**Agents do work + tests, NEVER commit or push.** The main orchestrator
collects diffs from each worktree and commits serially in main.

### Agent prompt pattern

```
You're in a worktree of __PROJECT_NAME__. Implement <issue>. Edit only
these files: <list>. Run the project's test suite to validate. DO NOT
`git commit`, DO NOT `git push`, and DO NOT pick or emit a version tag
— the orchestrator owns the tag namespace. When done, report:
- the modified files (list)
- the test command(s) that pass
- a one-paragraph summary of the wiring path
```

### Orchestrator merge loop

For each returning agent — **never `cd` into the worktree** (see "cwd
drift" above). Use `git -C` so the shell's cwd stays pinned to the
main checkout for the entire loop:

1. Extract the agent's diff WITHOUT moving cwd:
   `git -C ".claude/worktrees/agent-<id>" diff <base-sha> -- <files>`
   → a patch file under a temp dir. `<base-sha>` = the main tip at
   the moment the agents were dispatched.
2. Sanity-check scope: the `--stat` of that diff must list ONLY the
   agent's assigned files. Anything else is a stray edit — investigate
   before applying.
3. In the main checkout: `git apply "<tmp>/agent-<id>.patch"`.
4. `git add <the agent's files, named explicitly>` — never
   `git add -A` / `git add .`, which would sweep the
   `.claude/worktrees/` tree and any untracked cruft into the commit.
5. `git commit -m "<CC subject>"` — one commit per logical batch.
6. `git push origin main`. Keep `git push` in its OWN `Bash`
   command — a command that contains `git push` AND a later `-f`
   token (e.g. a chained `git worktree remove -f`) may false-match a
   `push -f` block pattern.
7. **Clean each consumed worktree** — in a command separate from any
   `git push`:
   - `git worktree remove -f -f .claude/worktrees/agent-<id>` (`-f -f`
     because agents launch with `locked` worktrees).
   - `git branch -d worktree-agent-<id>` (safe delete; uppercase `-D`
     may be hook-blocked — if `-d` refuses because the branch isn't
     reachable from main, the agent did real work that never made the
     merge; STOP and investigate before forcing). A clean delete
     prints `was <base-sha>` — confirm it matches the dispatch base,
     proving the agent never committed.
   - Remote agent branch deletion (`git push origin --delete
     worktree-agent-<id>`) may be hook-blocked. Batch these to the
     operator at session-wrap rather than asking N times mid-loop.

The orchestrator owns the tag namespace, the merge subject, the push
cadence, AND the per-merge cleanup. No collision is possible because
there's only one writer; no stale worktree pile-up because the
cleanup is part of the same step that consumed the agent's output.

### Session-wrap (before writing the handoff)

Even with per-merge cleanup, verify at session-wrap:

```bash
git stash list                          # should be empty
git worktree list | grep agent-         # should be empty
git branch | grep worktree-agent-       # should be empty
git ls-remote --heads origin | grep agent-  # batch this list to the operator for --delete authorization
```

Any non-empty result is a leak from a killed agent (its worktree
was never consumed by the merge loop). Drop the stash if its
`message` shows it belongs to a worktree branch + the work is in
main. Surface remote agent branches as a single bullet in the
handoff's Action #1 with the exact `git push origin --delete` line —
the operator needs to authorize destructive remote ops.

### Pre-flight constraints (orchestrator)

Before dispatching N agents:

- **Disjoint file matrix.** Two agents touching the same file is sequential — never parallel.
- **No regression in main first.** Run the full test suite in main; if a test is broken on main, agents will burn budget debugging "did I break this?". Fix main first.
- **Worktree exempt list current.** Verify any new file-walking gates exempt `.claude/worktrees/`.

### When parallel agents are the right tool

- Research / investigation across 4+ independent codebase questions.
- Code shipping ONLY when (a) the file-touch matrix is disjoint AND (b) the orchestrator-merge loop is staffed (i.e. you're available to merge serially as agents return). Otherwise sequential is faster.

### When parallel agents are the wrong tool

- Single shared file.
- Cross-cutting refactors where every agent needs to know the same type/interface shape.
- Doc fixes — sequential is essentially free for these.
- Anything where you can't sustain the merge loop in real time.

## See also

- `CLAUDE.md` — project rules · "Per item: highest-priority not-blocked → implement → hooks → commit → push → next."
- `.agent-kit/docs/context-framework.md` — doc-authoring framework and freshness gates

## 2026-07 addendum — native worktrees supersede the manual loop

Claude Code now ships worktree support natively: `claude --worktree <name>` (or `-w`) creates an
isolated checkout under `.claude/worktrees/<name>` on its own branch; `.worktreeinclude` copies
gitignored env files in; `claude agents` is the native dashboard for background sessions; and
subagents accept `isolation: worktree` frontmatter. Prefer these over the manual `git -C` loop
below (kept for pre-native versions and for what native does NOT cover: port/DB/env allocation
per stream, and setup commands — fresh checkouts have no node_modules). The kit's Tag-trailer
hook was REMOVED for the race documented here: tags live in the shared `.git` and the first
parallel committer wins. Tag releases from the orchestrator/main session only.
