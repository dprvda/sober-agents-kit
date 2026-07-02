---
frozen_at: 2026-07-02
---
# Container hosts (Railway / Fly / Render) — as of 2026-07
- WHY not serverless for agent/loop workloads: serverless timeouts (10s-15m) kill long AI work
  sessions; state is ephemeral; cold starts bite. Containers are boring and right.
- Fly: suspend/resume kills idle cost; scoped deploy tokens (fly tokens create deploy — NEVER
  fly auth token into an agent env). Railway: watch token scope — a blanket token in an agent
  environment wiped a production DB in 9 seconds (real 2026 incident).
- Per-invocation pricing landmine: a crawler hitting a paid-per-call endpoint turned $30 into
  $1,933 — cap and cache anything priced per call.
