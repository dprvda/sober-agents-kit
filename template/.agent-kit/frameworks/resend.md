---
frozen_at: 2026-07-02
---
# Resend (email) — as of 2026-07
- Native MCP, simple key auth. Domain DNS must be verified before sends work.
- Agent rule: transactional templates in code (testable); never send from an unverified domain;
  log every send with an idempotency key.
