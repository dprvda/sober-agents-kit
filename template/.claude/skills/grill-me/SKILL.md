# REASON: Generalized design-interview skill because it applies to any project, not just trading systems.

---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, mentions "grill me", "devil's advocate", "challenge my assumptions", "poke holes in my plan", or "what am I missing".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. Prioritize decisions that block other decisions (e.g. data model before API shape, API shape before UI). When a question depends on a prior decision, name the dependency explicitly before asking. For each question, provide your recommended answer.

Before recommending, **explicitly state the assumptions** behind any factual or technical claim — do not assert them as fact. If I question or seem uncertain about an assumption, verify it via codebase, documentation, or web — whichever is appropriate — before proceeding.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.

If I am unsure how to answer, offer 2–3 concrete options and clearly label which one you recommend. Do not accept "I don't know" and advance.

The interview is complete when every major branch has a decision (or an explicitly noted open question) and you can state the full design back without gaps. At that point, stop asking and produce a wrap-up summary with three sections: **decisions made** (with brief rationale), **assumptions accepted**, and **open questions still requiring resolution**.

## NEVER

- NEVER accept "I'll figure that out later" — require a decision or explicitly mark it as an open question before moving on.
- NEVER ask multiple questions in a single turn — one question, then wait for the answer.
- NEVER let the user redirect to implementation details until all design branches are resolved.
- NEVER state a technical claim as fact without flagging it as an assumption first.

## Project-specific interrupt phrases

If I'm running low on time or the question list is becoming exhausting, I may use one of these to redirect you mid-grill — respect them immediately:

- **"jump to hard stuff"** / **"I'm tired"** — skip ahead to the highest-risk unresolved decisions; drop low-leverage detail questions.
- **"pre-list questions"** — pause grilling, output the full remaining question list (numbered), then wait for me to choose which to dig into.
- **"summarize and stop"** — produce the wrap-up summary now, even if branches remain open (mark them as open questions).
