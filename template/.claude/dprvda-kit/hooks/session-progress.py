# REASON: the session-continuity hook — the research-validated fix for memory-written handoffs.
# PreCompact: injects a hard instruction to flush live state to .claude/session-progress.md BEFORE
# compaction destroys it. SessionStart is covered by inject_context_docs (progress file first in
# its corpus). Replaces nothing; upgrades the end-of-session /handoff into a finalize step.
import json, sys, os

def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    event = payload.get("hook_event_name", "")
    proj = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    prog = os.path.join(proj, ".claude", "session-progress.md")
    if event == "PreCompact":
        msg = ("CONTEXT IS ABOUT TO COMPACT. Before anything else: update .claude/session-progress.md "
               "with (1) current state — branch, running processes, exact next command; (2) what was "
               "done since the last entry, with file paths; (3) what FAILED and why (the most valuable "
               "field); (4) key decisions verbatim. Facts you skip now are gone after compaction.")
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreCompact", "additionalContext": msg}}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
