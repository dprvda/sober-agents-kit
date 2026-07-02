# Lessons (seed)

> Starter `lessons.md` for a new repo's memory. These are **portable** engineering lessons
> distilled from a real autonomous-coding project — none are domain-specific. Keep the ones that
> apply to your stack; add your own as real mistakes happen (that's the whole point of this file).

## Git & commit discipline

- **Run commits in the foreground with a short/no timeout.** Backgrounding a `git commit` and then
  long-polling for it invites a class of hangs (orphaned process holding the pre-commit lock).
  Pattern: `SECONDS=0 && git commit -F /tmp/msg.txt > /tmp/c.log 2>&1; echo "RC=$? TIME=${SECONDS}s"; git log --oneline -1`.
  A commit that "hangs" for minutes is almost never the work — it's a stuck lock; diagnose, don't wait.
- **Never bypass a failing hook** (`--no-verify`, `--skip-hooks`). The hook caught something; fix the cause.
- **Issue/PR writes to third-party repos require explicit per-post approval.** Drafting locally is free;
  posting is not. Your own repos are fine.

## Test & verify discipline

- **Run the FULL test suite before claiming "green",** not a single package/module. Per-package runs
  silently miss cross-module wiring and config failures.
- **A wall of identical failures across unrelated tests = one root cause** (an env var, a missing path,
  a harness misconfig), not N independent bugs. Find the single cause; read the suite's README for the
  canonical invocation before running.
- **A static grep test ("does the source contain string X") tests presence, not behavior.** Prefer a
  round-trip or data-completeness invariant.
- **Serialization tests must use the value the production caller actually passes** — a fixture that
  happens to match a hardcoded/wrong value passes while production silently emits garbage.

## Agent orchestration

- **Set the model explicitly on every sub-agent** — never rely on defaults. Strongest model for
  code-intel / forensic / adversarial-verification; mid-tier for research/summarize; never the
  cheapest tier for load-bearing reasoning.
- **Parallel LLM calls share no prompt cache** — fan out for latency, run sequentially to reuse cache/cost.
- **LLM judges can't do arithmetic or multi-step bookkeeping reliably** (version bumps, ID lookups,
  numeric comparisons). Compute those in code; use the LLM only for prose/shape/style judgments.
- **Parallel agents inflate filesystem side-effects** (build dirs, caches) that gate tools then scan —
  exempt agent worktree/artifact dirs from your gates, or they'll fire on phantom files.

## Platform gotchas (Windows / git-bash / WSL)

> Drop these if you're Linux/macOS-only.

- **`$VAR` and `$(...)` go EMPTY inside multi-line `wsl bash -lc '...'` invoked from git-bash.**
  Hardcode literal paths in that boundary, or you can `rm` the wrong thing.
- **`kill` does not reliably propagate to Windows child processes.** After killing, verify the process
  is actually gone (`ps -W | grep ...`).
- **Native Python can't traverse git-bash symlinks** — a path that resolves in the shell may be
  unreadable to a Python script; pass real paths.
- **A directory that is a running process's CWD can't be deleted on Windows** ("device or resource
  busy") — `cd` out first.

## Infrastructure

- **"Source of truth says X but the cached view still says Y" is a general class** (IAM/policy
  propagation, DNS TTL, package registries, CDN). After changing a permission/policy, expect a
  propagation lag before it takes effect; don't conclude "broken" immediately.
