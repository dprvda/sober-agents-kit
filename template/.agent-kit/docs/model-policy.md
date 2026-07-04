# Model policy — which model does which job (set it PER WORKFLOW, from the start)

Getting the model right **per stage** is not optional, and it must be set when a workflow or skill is
**LAUNCHED** — most skills default to a single model that is not the one each stage needs. Wire the model
per stage explicitly; do not accept the default. This is one of the first things to get right in a project,
because the wrong default quietly wastes money on cheap work and under-powers the hard steps.

## The tiers (the standard stack)

- **Reasoning, product judgment, design, architecture, and ALL planning → the top reasoning model
  (Fable 5).** Never delegate a design, architecture, or planning decision below it.
- **Small mechanical work, and bulk search / fetch / verify → a fast cheap model (Sonnet 5, medium
  effort).**
- **Well-specified coding and plan execution → a strong coding model (Opus, high effort; xhigh for plan
  execution).**

## Per workflow — assign the model per stage (the defaults differ)

- **Research — a deep-research workflow/skill.** Split the stages, do not run it all on one default model:
  - **scope** the research (shape the question, the angles, what to look for) → **Fable** (reasoning);
  - **search / fetch / verify** (the bulk gathering and checking) → **Sonnet 5 medium** (fast/cheap);
  - **synthesize** the final result → **Opus high** (strong).
- **Deep reference / competitor research — getting INSIDE real products** (browser automation + throwaway
  free-tier signups + reading the verification / magic code from an inbox): run it on **Opus high**. If the
  project ships this as a skill, use it; otherwise follow the project's own method doc.
- **Build work — Superpowers: brainstorm → write the plan → execute the plan.** ALL **planning** — the
  **brainstorm** and **writing the plan** — is **Fable**. **Executing the plan** — the implementer /
  subagent-driven-development agents — is **Opus at xhigh effort**. An executor never makes a design or plan
  decision; that belongs to the Fable planning stage.

## Multi-agent fan-out

The reasoning model (Fable) only for the synthesis step; the coding model (Opus) for coding / execution
agents; the fast model (Sonnet medium) for search / fetch / verify research agents.

---

Turn this into the project's own model-policy section once the project's skills are wired in (name the
project's deep-research and reference-research skills and their per-stage models explicitly).
