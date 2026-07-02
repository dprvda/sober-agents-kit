---
frozen_at: 2026-07-02
---
# Observability (Sentry / PostHog / OTel) — as of 2026-07
- Sentry and PostHog both ship official MCPs. OTel GenAI semantic conventions exist for LLM
  spans — use them for agent pipelines.
- The killer failure is SILENT success: dashboards green while writes land in the wrong table.
  Assert on OUTPUT COUNTS vs expectations, not just absence of exceptions.
