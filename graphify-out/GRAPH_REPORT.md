# Graph Report - .  (2026-06-12)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 319 nodes · 487 edges · 51 communities (31 shown, 20 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `e3b63784`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Content Review and Reporting|Content Review and Reporting]]
- [[_COMMUNITY_Commit Message Validation|Commit Message Validation]]
- [[_COMMUNITY_Documentation Freshness Checks|Documentation Freshness Checks]]
- [[_COMMUNITY_Markdown Link Validation|Markdown Link Validation]]
- [[_COMMUNITY_Installation and Setup Utilities|Installation and Setup Utilities]]
- [[_COMMUNITY_Context Injection and Document Processing|Context Injection and Document Processing]]
- [[_COMMUNITY_File Size and Symptom Detection|File Size and Symptom Detection]]
- [[_COMMUNITY_Git Commit and Freshness Testing|Git Commit and Freshness Testing]]
- [[_COMMUNITY_Linting and Security Checks|Linting and Security Checks]]
- [[_COMMUNITY_File Reason and Validation|File Reason and Validation]]
- [[_COMMUNITY_Git Commit Timestamp Management|Git Commit Timestamp Management]]
- [[_COMMUNITY_Git Tag Management|Git Tag Management]]
- [[_COMMUNITY_Repository Section Extraction|Repository Section Extraction]]
- [[_COMMUNITY_Gate Execution and Results|Gate Execution and Results]]
- [[_COMMUNITY_Script Launch and Sidecar Paths|Script Launch and Sidecar Paths]]
- [[_COMMUNITY_GitHub Nudge Commands|GitHub Nudge Commands]]
- [[_COMMUNITY_Serena Nudge Commands|Serena Nudge Commands]]
- [[_COMMUNITY_Serena MCP Server|Serena MCP Server]]
- [[_COMMUNITY_Foreground Git Nudge Commands|Foreground Git Nudge Commands]]
- [[_COMMUNITY_Install Script|Install Script]]
- [[_COMMUNITY_Uninstall Script|Uninstall Script]]
- [[_COMMUNITY_Global Rules Template|Global Rules Template]]
- [[_COMMUNITY_Lessons Seed Data|Lessons Seed Data]]
- [[_COMMUNITY_User Profile Template|User Profile Template]]
- [[_COMMUNITY_Audit Structure Skill|Audit Structure Skill]]
- [[_COMMUNITY_Caveman Skill|Caveman Skill]]
- [[_COMMUNITY_Compact Documents Skill|Compact Documents Skill]]
- [[_COMMUNITY_Grill-Me Skill|Grill-Me Skill]]
- [[_COMMUNITY_Handoff Skill|Handoff Skill]]
- [[_COMMUNITY_TDD Deep Modules|TDD Deep Modules]]
- [[_COMMUNITY_TDD Interface Design|TDD Interface Design]]
- [[_COMMUNITY_TDD Mocking|TDD Mocking]]
- [[_COMMUNITY_TDD Refactoring|TDD Refactoring]]
- [[_COMMUNITY_TDD Skill|TDD Skill]]
- [[_COMMUNITY_TDD Tests|TDD Tests]]
- [[_COMMUNITY_Issue Creation Skill|Issue Creation Skill]]
- [[_COMMUNITY_Write-A-Skill Skill|Write-A-Skill Skill]]
- [[_COMMUNITY_Zoom-Out Skill|Zoom-Out Skill]]

## God Nodes (most connected - your core abstractions)
1. `review_file()` - 12 edges
2. `main()` - 11 edges
3. `Verdict` - 11 edges
4. `main()` - 11 edges
5. `check_link()` - 10 edges
6. `main()` - 10 edges
7. `check_tracks_dir()` - 9 edges
8. `apply_review_block()` - 9 edges
9. `validate_format()` - 9 edges
10. `check_authored_md_coverage()` - 8 edges

## Surprising Connections (you probably didn't know these)
- `check_python_lint.py` --references--> `install.py`  [EXTRACTED]
  packs/python/README.md → INSTALL.md
- `check_binary_secrets.py` --references--> `install.py`  [EXTRACTED]
  packs/rust/README.md → INSTALL.md
- `check_cargo_audit.py` --references--> `install.py`  [EXTRACTED]
  packs/rust/README.md → INSTALL.md
- `check_cargo_vet.py` --references--> `install.py`  [EXTRACTED]
  packs/rust/README.md → INSTALL.md
- `claude-code-kit` --references--> `install.py`  [EXTRACTED]
  README.md → INSTALL.md

## Import Cycles
- None detected.

## Communities (51 total, 20 thin omitted)

### Community 0 - "Content Review and Reporting"
Cohesion: 0.11
Nodes (39): apply_review_block(), call_judge(), comment_char_for(), emit_report(), eprint(), get_api_key(), get_staged_content(), get_staged_diff() (+31 more)

### Community 1 - "Commit Message Validation"
Cohesion: 0.09
Nodes (36): build_judge_prompt(), call_judge(), classify_message(), commit_messages_since_tag(), commits_since_tag(), diff_stats(), extract_tag_trailer(), issue_is_actionable_block() (+28 more)

### Community 2 - "Documentation Freshness Checks"
Cohesion: 0.13
Nodes (29): check_authored_md_coverage(), check_freshness(), check_presence(), check_tracks_dir(), CheckError, effective_mtime(), _handle_ack_no_drift(), handoff_in_staged_commit() (+21 more)

### Community 3 - "Markdown Link Validation"
Cohesion: 0.11
Nodes (29): BrokenLink, check_link(), collect_md_files(), extract_anchors(), extract_links(), find_target_md(), is_external(), is_frozen() (+21 more)

### Community 4 - "Installation and Setup Utilities"
Cohesion: 0.34
Nodes (17): copy_payload(), install_pack(), is_text(), _load_settings(), log(), main(), Path, Copy src tree into dst with safe rules. Returns list of notes. (+9 more)

### Community 5 - "Context Injection and Document Processing"
Cohesion: 0.18
Nodes (16): _adr_index(), _build_corpus(), _chunks(), _emit(), _latest_handoff(), main(), _open_issues(), Ordered (label, text) items — the full injected corpus.      Generic order: (+8 more)

### Community 6 - "File Size and Symptom Detection"
Cohesion: 0.23
Nodes (12): classify(), compaction_framework_help(), detect_symptoms(), _encoded_cwd(), main(), Encode a path the way Claude Code encodes ~/.claude/projects/<cwd>/.      Subs, Return (tier_label, warn, block) for a path, or None if exempt.      WARN is d, Derived WARN threshold -- BLOCK minus the 15% headroom band. (+4 more)

### Community 7 - "Git Commit and Freshness Testing"
Cohesion: 0.33
Nodes (12): _commit_at(), _git_init(), _load_module(), main(), Write + add + commit `file_rel` with author/committer date set to     `age_hour, Write + `git add` `file_rel` WITHOUT committing -- leaves it in     the staged, Import check_doc_freshness via sys.path so dataclasses + type     machinery res, Run the gate's passes against repo. Returns the combined     error list. Reset (+4 more)

### Community 8 - "Linting and Security Checks"
Cohesion: 0.18
Nodes (6): install.py, check_python_lint.py, check_binary_secrets.py, check_cargo_audit.py, check_cargo_vet.py, claude-code-kit

### Community 9 - "File Reason and Validation"
Cohesion: 0.38
Nodes (7): CheckError, find_reason_marker(), iter_target_files(), main(), Read first ~30 non-blank lines of the file looking for a REASON     marker. Ret, validate_file(), Path

### Community 10 - "Git Commit Timestamp Management"
Cohesion: 0.29
Nodes (9): effective_mtime(), git_commit_ts(), _load(), Most-recent commit timestamp on the current branch that touched     `rel_path`., Filesystem mtime, with git-commit-time as a floor.      Returns `max(fs_mtime,, Drop the cache and force the next call to re-run `git log`.      Call this fro, Bulk-load per-path commit timestamps for `repo_root`.      No-op if already lo, reset() (+1 more)

### Community 11 - "Git Tag Management"
Cohesion: 0.43
Nodes (7): create_tag(), head_commit_message(), head_sha(), head_subject(), main(), Return the commit SHA the tag points to, or None if the tag does     not exist., tag_target_sha()

### Community 12 - "Repository Section Extraction"
Cohesion: 0.38
Nodes (6): extract_sections(), main(), Return repo root via $CLAUDE_PROJECT_DIR or cwd fallback., Return [(header, body), ...] for each requested section, in     file-order. Bod, repo_root(), Path

### Community 13 - "Gate Execution and Results"
Cohesion: 0.53
Nodes (3): GateResult, main(), run_gate()

### Community 14 - "Script Launch and Sidecar Paths"
Cohesion: 0.60
Nodes (4): main(), Mirror .claude/dprvda-kit/gates/critic_llm.py::sidecar_path_for so the hook, sidecar_path_for(), Path

### Community 15 - "GitHub Nudge Commands"
Cohesion: 0.60
Nodes (4): build_nudge(), main(), parse_first_words(), Return (subcommand, action) — e.g. ('issue', 'view') for     ``gh issue view 64

### Community 16 - "Serena Nudge Commands"
Cohesion: 0.70
Nodes (4): build_nudge(), is_code_path(), is_identifier(), main()

### Community 17 - "Serena MCP Server"
Cohesion: 0.40
Nodes (4): serena, start-mcp-server, github, serena

## Knowledge Gaps
- **28 isolated node(s):** `install.sh script`, `Path`, `Path`, `serena`, `start-mcp-server` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `Copy src tree into dst with safe rules. Returns list of notes.`, `install.sh script`, `Drop the cache and force the next call to re-run `git log`.      Call this fro` to the rest of the system?**
  _107 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Content Review and Reporting` be split into smaller, more focused modules?**
  _Cohesion score 0.10685249709639953 - nodes in this community are weakly interconnected._
- **Should `Commit Message Validation` be split into smaller, more focused modules?**
  _Cohesion score 0.08708708708708708 - nodes in this community are weakly interconnected._
- **Should `Documentation Freshness Checks` be split into smaller, more focused modules?**
  _Cohesion score 0.12903225806451613 - nodes in this community are weakly interconnected._
- **Should `Markdown Link Validation` be split into smaller, more focused modules?**
  _Cohesion score 0.11182795698924732 - nodes in this community are weakly interconnected._