---
frozen_at: 2026-07-02
---
# Stack guide — API service / backend (agent-native defaults, verified 2026-07)

Injected by /sober-setup as `docs/STACK.md`.

## The stack
| Layer | Pick | Agent surface |
|---|---|---|
| Language | TypeScript (Hono/Express) or Python (FastAPI); Go/Rust only when perf is the product | typed + strict lint |
| Hosting | container platform (Railway/Fly/Render); serverless only for spiky request/response | long-lived state, no cold-start surprises |
| Database | Neon Postgres (official MCP) | branch per migration test |
| Auth | key auth for machine clients; WorkOS/Clerk for humans | agents integrate keys, not OAuth dances |
| Observability | Sentry + OTel; structured logs | errors must be loud |

## Best practices for the AI agent working here
- Contract first: OpenAPI/types define every endpoint BEFORE implementation; tests generated
  against the contract. A frontend expecting `/api/v1/x` while the backend serves `/api/x` is a
  100%-failure class — one source of truth for routes.
- Migrations + lockfiles are main-session-only in parallel work.
- Every external call: timeout, retry with backoff, and a circuit breaker; rate-limit headers
  respected (429 is a signal, not an error to swallow).
- Secrets via env/vault only; the agent works with scoped dev keys; production credentials are
  brokered, never in the agent's environment.
- Load-bearing changes need one runnable check (a smoke script or test) the agent RUNS before
  claiming done — fresh evidence in the same message.
