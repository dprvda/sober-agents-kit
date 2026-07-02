---
frozen_at: 2026-07-02
---
# Stack guide — content / media / video pipeline (agent-native defaults, verified 2026-07)

Injected by /setup-pravda-skills as `docs/STACK.md`.

## The stack
| Layer | Pick | Agent surface |
|---|---|---|
| Site/render | Next.js static-first; content as data (markdown + frontmatter) | adding content never edits src/ |
| Video | Remotion (React = typed, testable comps) + FFmpeg | deterministic renders, frame-exact |
| Images | gpt-image-2 class generation for scenes; DETERMINISTIC renderers for any chart with real values | generated geometry lies about data |
| Hosting | Vercel (site) + local GPU or a container for renders | renders outlive serverless limits |
| Storage | object storage (Blob/S3) for media; git-lfs for binaries in repo | never mp3/mp4 in plain git |

## Best practices for the AI agent working here
- Numbers are sacred: every figure rendered into content traces to a source. Generated images
  NEVER draw value-encoding geometry (bars/lines) — deterministic renderers own charts.
- Every visual result gets OPENED/screenshotted and looked at before claiming done. Validate
  rendered video by reading sampled frames (garbled text, dead tails, black frame 0).
- Content pipeline state lives in a ledger/manifest, appended per artifact event — file presence
  is not state.
- Cache per-chunk expensive outputs (TTS/render) keyed on input + params, so re-runs are gap-fills.
- Batch = two-phase: generate + validate ALL cheap text first, only then spend GPU/paid renders.
