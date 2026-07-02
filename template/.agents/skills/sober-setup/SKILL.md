---
name: sober-setup
description: Audit or update THIS project's sober-agents-kit setup (re-run the interview, apply upstream kit changes, activate deferred pieces like the stack guide or session memory). Trigger on "/sober-setup", "audit my agent setup", "update the kit".
---

# /sober-setup — audit/update stub (installed project)

This project was set up by [sober-agents-kit](https://github.com/dprvda/sober-agents-kit). The
interview playbook lives in the kit repo, not here, so updates never drift.

**Do this now:**
1. Locate a clone of the kit repo; if none exists, `git clone
   https://github.com/dprvda/sober-agents-kit` into a sibling or temp directory.
2. Read the kit's `setup/INTERVIEW.md` in full and follow its **"Auditing an existing install"**
   section against this project (the install manifest is `.claude/dprvda-kit/kit.config.json`).
