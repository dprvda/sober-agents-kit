---
frozen_at: 2026-07-02
---
# Stack guide — SaaS web app (agent-native defaults, verified 2026-07)

Injected by /sober-setup as `docs/STACK.md`. Every pick below passes the agent-legibility
test: full API + key auth, an OFFICIAL MCP server, machine-readable docs, a free tier the agent
can self-serve. Sources: vendor docs verified 2026-07 (Vercel/Neon/Stripe/Clerk/Resend/Sentry).

## The stack
| Layer | Pick | Agent surface |
|---|---|---|
| Framework | Next.js (TypeScript, strict) | typed + lint = the agent's guardrails |
| Hosting | Vercel | official MCP (mcp.vercel.com), CLI, preview deploys |
| Database | Neon Postgres | official MCP (mcp.neon.tech, API-key auth), sub-second branching |
| Auth | Clerk (or Auth.js if no budget) | agent-experience CLI, docs are machine-readable |
| Payments | Stripe | official Agent Toolkit + hosted MCP (mcp.stripe.com); restricted keys |
| Email | Resend | native MCP, key auth |
| Observability | Sentry + PostHog | official MCPs |

## Best practices for the AI agent working here
- One AGENTS.md at the repo root routes everything; CLAUDE.md imports it. Keep under 200 lines.
- Migrations, lockfiles, `.env*`, and deploy config are MAIN-SESSION-ONLY files — never edit them
  from a parallel worktree stream.
- DB changes go through migration files reviewed before apply, never raw SQL against prod. Use a
  Neon branch per risky change; it is copy-on-write and disposable.
- Payments: only RESTRICTED Stripe keys in dev; the agent never sees a live secret key
  (credential brokering — the human pastes live keys into the platform dashboard only).
- Every UI change: screenshot at 1440/768/375 and READ the screenshot before claiming done.
- Deploys: push to the branch, let the platform preview-deploy, verify the preview URL, then merge.
