---
frozen_at: 2026-07-02
---
# Playwright (the agent's eyes) — as of 2026-07
- npx playwright screenshot <url> <out.png> — then READ the png (multimodal) before claiming a
  UI change works. Loop: capture → look → fix → recapture at 1440/768/375 widths.
- For flows: codegen + the test runner; keep browser installs cached (npx playwright install).
