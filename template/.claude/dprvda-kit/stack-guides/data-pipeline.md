---
frozen_at: 2026-07-02
---
# Stack guide — data pipeline / scraper / ETL (agent-native defaults, verified 2026-07)

Injected by /setup-pravda-skills as `docs/STACK.md`.

## The stack
| Layer | Pick | Agent surface |
|---|---|---|
| Language | Python (typed w/ pyright) or TypeScript | strict types = agent guardrails |
| Orchestration | plain scripts + cron first; a queue only when proven needed | boring wins |
| Hosting | long-lived container (Railway/Fly/Render), NOT serverless | agent loops outlive serverless timeouts (10s-15m) |
| Scraping | Apify (official API, actor store) or Firecrawl (MCP) | key auth, per-run pricing |
| Storage | Neon Postgres (official MCP) + object storage | branchable, key auth |
| Observability | structured logs + dead-letter table | silent failure is THE pipeline killer |

## Best practices for the AI agent working here
- Every fetch has a retry with backoff AND a dead-letter path. A 429 swallowed as a generic error
  is the documented way pipelines die silently.
- Every pipeline run writes a run record (started/finished/counts/errors) BEFORE and AFTER work.
  State lives in the DB, never inferred from file presence.
- Budget caps on every LLM call in the pipe (`--max-budget-usd` equivalents; cap retries).
- Idempotency keys on any paid external call; re-runs must be safe by construction.
- Proxies/keys resolve from env or a vault, never hardcoded; datacenter proxies before
  residential (cost); one env var switches the whole provider.
- Green dashboards measure health, not correctness: assert on OUTPUT COUNTS against expectations,
  not just "no exceptions."
