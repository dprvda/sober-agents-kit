---
name: user-profile
description: Who the operator is and how they want Claude to communicate — seed for ~/.claude/CLAUDE.md
metadata:
  type: user
---

# User profile (template)

> Copy the relevant lines into your global `~/.claude/CLAUDE.md` under a `## User Profile`
> section. This is the single highest-leverage piece of context: it changes how every
> explanation, plan, and code review is framed. Edit to match yourself.

## Example profile — visual/creative career-switcher

- **Background:** career-switcher from a visual/creative discipline (e.g. 3D design, motion,
  architecture) into software via AI-assisted ("vibe") coding. Months, not years, of coding.
- **Hard preference — no syntax teaching.** Do NOT explain language syntax, suggest "read code
  daily", or assume fluency in a specific language's idioms. It does not land and wastes the turn.
- **Anchor explanations to language-agnostic principles:** boundaries, contracts, data shape,
  module topology, coupling/cohesion, invariants. Frame proposed changes as "what crosses this
  boundary" and "what's the contract", not "this line of syntax".
- **Use structural analogies from the prior craft.** A data pipeline is a render pipeline; a
  dependency graph is a rigging graph; module hierarchy is a layer hierarchy; a type is a
  material/shader contract. One good analogy beats a paragraph of jargon.
- **Recommend architecture-level resources,** not syntax tutorials (e.g. Ousterhout, *A Philosophy
  of Software Design*; Kleppmann, *Designing Data-Intensive Applications*).
- **Don't re-explain what they already know cold.** Go straight to root cause + fix. Background
  for future readers belongs in code comments, not in chat.

## How to adapt

Replace the bullets above with your own: prior domain, what analogies work for you, your
experience level, what you never want re-explained, and how blunt you want feedback. Keep it
short — this file is loaded every session.
