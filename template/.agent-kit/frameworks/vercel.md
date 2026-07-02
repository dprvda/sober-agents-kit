---
frozen_at: 2026-07-02
---
# Vercel — as of 2026-07
- Official MCP: mcp.vercel.com (deploys, logs, projects from the agent).
- Edge Functions are NOT recommended anymore; Fluid Compute is the default (full Node, same
  regions/price). Middleware supports full Node. Default function timeout is now 300s.
- vercel.ts (typed config via @vercel/config) replaces vercel.json as the recommended path.
- AI Gateway: zero-markup, BYOK, "provider/model" strings — default for AI calls.
- Vercel Postgres/KV are GONE — use marketplace databases (Neon).
