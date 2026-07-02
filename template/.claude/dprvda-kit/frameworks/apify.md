---
frozen_at: 2026-07-02
---
# Apify (scraping) — as of 2026-07
- Actor store: many actors are mock/demo on free tiers — VERIFY an actor returns real data
  before building on it. Per-run pricing: set a spend guard and check account spend in code.
- Datacenter proxies by default (residential is metered and expensive) — one env switch.
- Webhooks retry ~6x with a ~9-hour ceiling; make handlers idempotent (Idempotency-Key).
