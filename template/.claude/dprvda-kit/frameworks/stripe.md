---
frozen_at: 2026-07-02
---
# Stripe — as of 2026-07
- Official Agent Toolkit (MCP-format tools) + hosted MCP at mcp.stripe.com (OAuth per spec;
  restricted-key Bearer fallback).
- Agent rule: RESTRICTED keys only in dev; the agent never sees a live secret key (the human
  pastes live keys into dashboards only). Idempotency keys on every mutating call.
