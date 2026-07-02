# The gates — mechanics reference (linked from AGENTS.md, lives next to the machinery)

Dispatcher: `run_gates_parallel.py` (phase 1 serial → phase 2 parallel), wired by
`.pre-commit-config.yaml`. Every gate prints its own fix instructions when it fires.

| Gate | Blocks |
|---|---|
| `check_secrets` | secret-shaped strings in the staged diff |
| `critic_llm` (AI judge) | a second, independent AI reviews each staged file against YOUR project rules. Blank `LLM_JUDGE_API_KEY` ⇒ soft-pass |
| `critic_llm_commit` | malformed Conventional Commits (`<type>(<scope>): <subject ≤99>` → blank → body explaining WHY when the diff is big) |
| `check_file_reason` | any new script without a `# REASON:` header (≥30 chars — forces reuse-vs-create thinking) |
| `check_doc_freshness` | docs drifting from the code they track (`tracks_dir:`) or undated snapshots (`frozen_at:`) |
| `check_links` | broken `.md` cross-references |
| `check_md_size` | docs growing past what an AI actually reads |
| `check_force_push` (pre-push) | force-pushes + remote branch deletions, for every tool and every clone |

## `=== LLM_REVIEW_BLOCK ===` protocol

The judge prepends a comment block to a flagged source file: top marker → `Summary:` → numbered
`L<line> (severity, category): issue -> fix` → end marker. When you see one: (1) read every
item, (2) **fix the code** (deleting the block alone re-triggers it next commit), (3) remove the
whole block, (4) re-stage + re-commit.

## Escape hatches (audited, deliberate — never routine)

- `--ack-no-drift PATH --reason '<≥30 chars>'` — doc-freshness, pure mtime ripple with no body drift.
- `# SECRET_OK: <reason>` — a line the secrets gate should skip (e.g. a documented example key shape).
- `AGENT_KIT_ALLOW_FORCE_PUSH=1` — one reviewed, deliberate force push.

Tuning: thresholds and exempt dirs are constants at the top of each gate script.
