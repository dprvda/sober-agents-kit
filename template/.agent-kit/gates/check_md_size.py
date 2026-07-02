# REASON: universal per-doc character-budget gate over all authored .md in the repo; tier-based thresholds prevent docs from drifting past readable size because char budgets align 1:1 with the SessionStart context-injection chunk size; no existing gate enforces per-doc character limits.
"""Per-doc character-size gate.

For every authored Markdown file in the repo, count characters
(`len(text)`) and check against a tier-specific budget. Character-
based so budgets align 1:1 with the SessionStart context-injection
hook -- capped at 10000 chars per chunk, so an "essential" doc uses
~2 chunks, a handoff doc uses ~1.

  Tier                                      Block
  ----                                      -----
  CLAUDE.md (loaded every session)          16800
  MEMORY.md (~/.claude auto-memory)         24000
  docs/ essentials (all docs/*.md)          19500
  Session handoffs (.claude/handoffs/)      19500
  Folder READMEs (top-level)                19200
  Sub-folder READMEs                        12000
  Other authored .md                        14400

WARN is derived, never declared: warn_for(block) = round(block * 0.85),
so every doc keeps a uniform 15% headroom band below its hard cap.

Out-of-repo files (auto-memory) are also checked -- see EXTERNAL_FILES.
The script normally walks `git ls-files` only; EXTERNAL_FILES is a
hardcoded extension for files that live outside the repo but are loaded
into every session preamble (and therefore have to stay tight too).

On warn/block, emit framework-grounded recommendations explaining HOW
to compact without losing helpful info -- Diataxis (one purpose per
doc), DRY (link don't duplicate), progressive disclosure (summary
first, details linked), information mapping (one topic per section),
bullet > prose, reference > inline, no-build prose.

Usage:
    python scripts/check_md_size.py            # CI gate (block on block, warn on warn)
    python scripts/check_md_size.py --strict   # exit 1 on warn too
    python scripts/check_md_size.py --recs FILE  # show recs for one file
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Folders / paths the gate skips entirely (auto-generated, mirrored,
# archived, vendored). Edit this list to match your project layout.
EXEMPT_PREFIXES = (
    ".claude/",          # Claude runtime dirs (handoffs, session files) — not project prose
    ".agent-kit/",       # the kit's own machinery (gates, frameworks, docs)
    ".agents/",          # cross-tool skills dir
    "archive/",
    "docs/archive/",
    "vendor/",
    "node_modules/",
    "target/",
    "dist/",
    # Planning and research docs are one-shot inventories that shouldn't
    # fire the size gate.
    "docs/planning/",
    "docs/research/",
)

# WARN fires 15% below BLOCK -- single source of truth, so every tier
# declares only its BLOCK cap and WARN is derived. The headroom band
# lets a doc grow within a session before hitting the hard cap.
WARN_HEADROOM = 0.15


def warn_for(block: int) -> int:
    """Derived WARN threshold -- BLOCK minus the 15% headroom band."""
    return round(block * (1.0 - WARN_HEADROOM))


# Tier definition: (path regex, label, BLOCK cap). WARN is derived via
# warn_for(block). First match wins; most-specific regex first.
#
# NOTE: These tiers are EXAMPLES -- edit them to match your project's
# actual directory structure. The char caps (10000 chars per SessionStart
# injection chunk) should be preserved when resizing tiers.
TIERS = [
    # Session handoffs -- injected into every fresh session; 19500 chars
    # = 2 injection chunks.
    (re.compile(r"^\.claude/handoffs/.+\.md$"),
     "handoff", 19500),
    # essentials -- every top-level docs/*.md is an AI-readable essential.
    # 19500 chars = 2 SessionStart injection chunks.
    (re.compile(r"^docs/[^/]+\.md$"),
     "essential", 19500),
    # CLAUDE.md -- loaded into EVERY session preamble; kept tight.
    (re.compile(r"^CLAUDE\.md$"),
     "claude-md", 16800),
    # Project-rules / framework docs (.agent-kit/adapters/claude/README.md, AGENTS.md, README.md).
    (re.compile(r"^(AGENTS|README)\.md$"),
     "framework-rules", 19500),
    # Sub-folder READMEs (deep), e.g. src/foo/README.md.
    (re.compile(r"^[^/]+/.+/README\.md$"),
     "sub-folder-readme", 12000),
    # Top-level folder READMEs -- scripts/, deploy/, etc.
    (re.compile(r"^[^/]+/README\.md$"),
     "folder-readme", 19200),
    # Per-folder index pages under docs/.
    (re.compile(r"^docs/.+/(index|README)\.md$"),
     "folder-readme", 19200),
    # Catch-all for any other authored .md.
    (re.compile(r"^.*\.md$"),
     "other", 14400),
]


def _encoded_cwd(p: Path) -> str:
    """Encode a path the way Claude Code encodes ~/.claude/projects/<cwd>/.

    Substitution rule: any non-alphanumeric char becomes '-'.
    """
    return re.sub(r"[^a-zA-Z0-9]", "-", str(p))


# Auto-memory files (LIVE OUTSIDE REPO but loaded into every session preamble).
# `git ls-files` doesn't see them, so they need explicit registration here.
# MEMORY.md historically bloated across sessions because nothing enforced
# its size. Now it does.
EXTERNAL_FILES: list[tuple[Path, str, int]] = [
    (
        Path.home() / ".claude" / "projects" / _encoded_cwd(REPO_ROOT) / "memory" / "MEMORY.md",
        "memory-index",
        24000,  # BLOCK ~24 KB; WARN derived via warn_for()
    ),
]


# Framework-grounded compaction recommendations. Each emits when a
# specific symptom is detected; recommendations cite the framework for
# context (Diataxis / DRY / etc.) so authors learn the WHY.
@dataclass
class Symptom:
    name: str
    matches: callable  # body -> bool
    recommendation: str


SYMPTOMS: list[Symptom] = [
    Symptom(
        name="long_prose_paragraph",
        matches=lambda body: any(
            len(p.strip()) > 600 and not p.strip().startswith(("```", "|", "- ", "* ", "1. "))
            for p in body.split("\n\n")
        ),
        recommendation=(
            "**Bullet > prose** (info mapping): replace 600+ char paragraphs with bulleted "
            "lists or compact tables. Each bullet = one fact. Tables are denser still."
        ),
    ),
    Symptom(
        name="duplicated_section_header",
        matches=lambda body: len({line.strip() for line in body.splitlines() if line.startswith("##")}) <
                             sum(1 for line in body.splitlines() if line.startswith("##")),
        recommendation=(
            "**One topic per section** (info mapping): duplicate ## headers detected -- "
            "consolidate into a single section per topic. If two sections cover related "
            "ideas, merge them under one header with sub-bullets."
        ),
    ),
    Symptom(
        name="filler_phrases",
        matches=lambda body: any(
            phrase in body.lower() for phrase in (
                "it's worth noting", "it's important to note", "as we discussed",
                "as covered in section", "as mentioned earlier", "in this section we will",
                "this section describes", "this document covers", "the purpose of this",
                "as mentioned above", "needless to say",
            )
        ),
        recommendation=(
            "**No-build prose** (Strunk & White): drop filler phrases like 'It's worth noting', "
            "'As we discussed', 'This section describes'. Show the fact directly. "
            "Each removed filler frees ~10-30 tokens."
        ),
    ),
    Symptom(
        name="three_plus_mermaid",
        matches=lambda body: body.count("```mermaid") >= 3,
        recommendation=(
            "**Reference > inline** (DRY): 3+ Mermaid diagrams in one doc -- keep AT MOST 1-2 "
            "for the load-bearing concepts. Replace others with a sentence + a link to a "
            "deeper doc OR a small text/table representation. Mermaid blocks are token-heavy."
        ),
    ),
    Symptom(
        name="missing_progressive_disclosure",
        matches=lambda body: not (
            any(line.startswith("## ") for line in body.splitlines()[:50])
            and any(body.lower().count(token) >= 1 for token in ("see ", "->", "->"))
        ) and len(body) > 3600,
        recommendation=(
            "**Progressive disclosure** (Diataxis): doc lacks early-section anchors AND "
            "cross-references. Lead with a one-paragraph summary + 'Sections:' table; bury "
            "details below; use 'See [docs/X.md](X.md)' rather than re-explaining."
        ),
    ),
]


def classify(rel: str) -> tuple[str, int, int] | None:
    """Return (tier_label, warn, block) for a path, or None if exempt.

    WARN is derived from the tier's BLOCK cap via warn_for()."""
    for prefix in EXEMPT_PREFIXES:
        if rel.startswith(prefix):
            return None
    for pattern, label, block in TIERS:
        if pattern.match(rel):
            return label, warn_for(block), block
    return None


def detect_symptoms(body: str) -> list[Symptom]:
    return [s for s in SYMPTOMS if s.matches(body)]


def compaction_framework_help() -> str:
    return (
        "\n  -- Compaction framework (apply in order) --\n"
        "  1. Diataxis: ONE doc, ONE purpose (tutorial / how-to / reference / explanation).\n"
        "  2. DRY: link, don't duplicate. Cross-reference other essentials and READMEs.\n"
        "  3. Progressive disclosure: lead with the headline; bury details below; use\n"
        "     'See [foo.md](foo.md)' instead of inlining.\n"
        "  4. Information mapping (Robert Horn): one topic per section, bullets > prose,\n"
        "     tables > bullets when listing parallel facts.\n"
        "  5. No-build prose (Strunk & White): drop 'It's worth noting',\n"
        "     'This section describes', 'As we discussed'. Show the fact directly.\n"
        "  6. Reference > inline: link to source code (README, git log) for content\n"
        "     that drifts; link AI to gh issue list for backlog.\n"
        "  7. One Mermaid max per doc unless absolutely load-bearing.\n"
        "  Use --recs <file> for symptom-specific recommendations on a single file."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 on warn too (default: warn-only on warn, block on block)")
    ap.add_argument("--recs", type=str, default=None,
                    help="Show framework recommendations for ONE file by path")
    args = ap.parse_args()

    # Collect all .md files (git-tracked + untracked, excluding gitignored).
    # Use git ls-files for tracked + git ls-files --others --exclude-standard for new.
    import subprocess
    try:
        tracked = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "*.md"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        untracked = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "--others", "--exclude-standard", "*.md"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
    except subprocess.CalledProcessError:
        tracked = []
        untracked = []
    md_files = sorted(set(tracked + untracked))

    if args.recs:
        # Single-file mode for ad-hoc help.
        p = REPO_ROOT / args.recs
        if not p.exists():
            print(f"file not found: {args.recs}", file=sys.stderr)
            return 2
        body = p.read_text(encoding="utf-8")
        chars = len(body)
        tier = classify(args.recs)
        print(f"\n  {args.recs}: {chars} chars (tier: {tier[0] if tier else 'exempt'})")
        if tier:
            print(f"  Budget: warn {tier[1]}, block {tier[2]}")
        symptoms = detect_symptoms(body)
        if symptoms:
            print(f"\n  Symptoms detected ({len(symptoms)}):")
            for s in symptoms:
                print(f"\n  - {s.recommendation}")
        else:
            print("\n  No bloat symptoms detected.")
        print(compaction_framework_help())
        return 0

    block_count = 0
    warn_count = 0
    rows = []
    # SERIAL_OK_LOOP: bounded by repo .md count; per-file len() is instant
    for rel in md_files:
        tier = classify(rel)
        if tier is None:
            continue
        label, warn_t, block_t = tier
        p = REPO_ROOT / rel
        if not p.exists():
            continue
        try:
            body = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        chars = len(body)
        status = "OK"
        if chars >= block_t:
            status = "BLOCK"
            block_count += 1
        elif chars >= warn_t:
            status = "WARN"
            warn_count += 1
        rows.append((rel, label, chars, warn_t, block_t, status, body))

    # External (out-of-repo) files -- auto-memory MEMORY.md etc.
    # SERIAL_OK_LOOP: tiny list (1 entry today); per-file len() is instant
    for ext_path, ext_label, ext_block in EXTERNAL_FILES:
        ext_warn = warn_for(ext_block)
        if not ext_path.exists():
            continue
        try:
            ext_body = ext_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        ext_chars = len(ext_body)
        ext_status = "OK"
        if ext_chars >= ext_block:
            ext_status = "BLOCK"
            block_count += 1
        elif ext_chars >= ext_warn:
            ext_status = "WARN"
            warn_count += 1
        rows.append((str(ext_path), ext_label, ext_chars, ext_warn, ext_block, ext_status, ext_body))

    # Print only WARN/BLOCK rows (OK is silent unless very verbose)
    flagged = [r for r in rows if r[5] != "OK"]
    print(f"[check_md_size] {len(md_files)} .md files (+{len(EXTERNAL_FILES)} external); {len(flagged)} flagged ({warn_count} warn, {block_count} block)")
    if flagged:
        print()
    for rel, label, chars, warn_t, block_t, status, body in flagged:
        # Show the threshold actually crossed.
        thr = block_t if status == "BLOCK" else warn_t
        print(f"  {status:5}  {chars:6d}/{thr} chars  [{label}]  {rel}")
        symptoms = detect_symptoms(body)
        for s in symptoms[:3]:  # cap at 3 recs per file
            print(f"         {s.recommendation}")
        print()

    if block_count > 0:
        print(
            f"  FAIL -- {block_count} doc(s) over BLOCK budget. Trim before committing.\n"
            f"  Use --recs <file> for per-file framework recommendations.",
            file=sys.stderr,
        )
        print(compaction_framework_help(), file=sys.stderr)
        return 1

    if warn_count > 0:
        print(
            f"\n  {warn_count} warn(s) -- consider trimming. Block kicks in at the higher threshold.\n"
            f"  Use --recs <file> for framework-specific suggestions."
        )
        if args.strict:
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
