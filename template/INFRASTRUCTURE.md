# INFRASTRUCTURE & ARSENAL — what this project already has (use it; do NOT re-download or reinvent)

> Read this once. It is everything already set up for this project — the stack, the services you hold keys
> for, the local systems on your machine, and the existing engines you can reuse. **Do not ask "do we have
> X," do not re-download a tool that is already installed, do not build a new system when one already exists
> — check here first.** Exact API-key names live in the git-ignored `INFRASTRUCTURE.keys.local.md` (local
> only), never in this committed file (the repo may go public).

## The stack

<!-- FILL IN: framework, hosting, sign-in/accounts, database, storage, where heavy/background compute runs,
     deploy target. Delete this comment once filled. -->

## Services we already hold keys for (USE these — do NOT sign up for a new one)

List WHAT is available, not the exact key names (those go in the git-ignored keys file). If you need a
capability that is NOT listed, ask the owner BEFORE signing up for a new service.

<!-- FILL IN: e.g. LLM (which pool / models), images, voice, email (send + inbox), browser automation,
     scraping/proxies, web search, news feeds, analytics, deploy, code host, social, search console. -->

## Local systems ALREADY set up on this machine — do NOT re-download or reinstall

<!-- FILL IN: e.g. a local model / voice / inference server already installed + how to start it + its ports,
     the GPUs, any local models. State plainly "already installed — do NOT re-download / re-create," so an
     agent never re-fetches a model or venv that is already on this machine. -->

## Existing engines — USE these, do NOT invent a new one

<!-- FILL IN: the built, working systems you can reuse (a video renderer, a research pipeline, a code graph,
     an audio pipeline, …) and where each one lives — so an agent reuses the engine instead of writing a new
     one from scratch. -->

## Keys: how to fetch (exact names are git-ignored)

Never hardcode a key, never commit one. The exact key-store item names + the fetch commands live in the
git-ignored, local-only `INFRASTRUCTURE.keys.local.md`. Read it to resolve a name, then fetch the value at run
time. Per-app keys go in the deploy env + the local `.env`, never in git.

## The rule

It is already set up — use it. Don't ask "do we have X," don't re-download an installed tool, don't reinvent
an existing engine.
