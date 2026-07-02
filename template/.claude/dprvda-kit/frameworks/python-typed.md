---
frozen_at: 2026-07-02
---
# Typed Python — as of 2026-07
- Strict typing (pyright) + ruff = the agent catches its own mistakes before runtime.
- Every pipeline run writes a run record (started/finished/counts/errors); state in the DB,
  never inferred from file presence. Dead-letter every failed item; 429 is a signal, not noise.
- Budget-cap every LLM call; retries with backoff + jitter; idempotency on paid calls.
