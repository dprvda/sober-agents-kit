---
frozen_at: 2026-07-02
---
# Next.js — as of 2026-07
- Current major (16.x) has BREAKING changes vs your training: APIs, conventions, file structure.
  NEVER write Next code from memory: READ the version's own docs at node_modules/next/dist/docs/
  first — they ship with the install and match the exact version.
- App Router is the default; server components first, client islands surgical.
- Agent practice: after any Next upgrade, re-read the docs dir before touching src/.
