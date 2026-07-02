---
frozen_at: 2026-07-02
---
# Graphify (code knowledge graph) — what it is and why
- Turns any repo into a persistent knowledge graph (files, symbols, calls, docs) with query/
  path/explain tools. One graph query replaces fanning out across 10 files when orienting.
- Ships as a skill in this kit. Usage: /graphify . builds graphify-out/; then
  graphify query "how does X work" · graphify explain "Symbol" · graphify path "A" "B".
- Agent rule: when graphify-out/ exists, treat architecture questions as graph queries FIRST.
