---
frozen_at: 2026-07-02
---
# Neon Postgres — as of 2026-07
- Official MCP: mcp.neon.tech (OAuth AND plain API-key auth) — natural-language projects,
  queries, migrations. 80%+ of new Neon databases are agent-created (vendor-reported).
- Killer feature for agents: sub-second copy-on-write BRANCHING. Test every risky migration on
  a disposable branch first; never raw SQL against the main branch.
- Serverless driver for serverless hosts; ordinary pg for containers.
