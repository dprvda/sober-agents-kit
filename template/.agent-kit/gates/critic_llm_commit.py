# USER-AUTHORIZED 2026-04-29: unavailable_pass behavior — same as
# .agent-kit/gates/critic_llm.py, when the judge API is unreachable / key
# missing / call fails, the gate exits 0 and the commit proceeds.
# Best-effort AI judge, not a hard gate. NOT a banned bypass — fires
# only on a verifiable provider-outage condition, no user toggle.
# REASON: Conventional-Commits validator that uses an LLM as an optional cross-check.
# A deterministic, language-agnostic phase validates the message format (type/scope/
# subject length, blank line, body-required threshold) and computes the SemVer Tag:
# bump from the cumulative commit set in PURE CODE — the LLM is never trusted with
# arithmetic. A second optional phase asks the judge to cross-check type-vs-diff
# alignment, scope-vs-paths, and body adequacy, because no regex can tell whether a
# `fix:` subject matches a 500-line feature diff. Fires as a commit-msg hook.
# Implements `unavailable_pass` (USER-AUTHORIZED 2026-04-29) when the API is not
# reachable so an offline session still commits.
"""Validate commit messages as Conventional Commits + judge content.

Runs as a `commit-msg` stage hook (after the editor closes, before the
commit lands). Reads the prepared commit message and the staged diff,
validates format + SemVer tag deterministically, then optionally sends
both to the configured LLM judge for a content cross-check.

Verdict:
- BLOCK: hard format errors OR (from the LLM) a clear type-vs-diff
  mismatch (e.g. `fix:` with 500 LOC of new code → "should be feat:")
- WARN: prose suggestions, soft format issues
- OK: format-clean + substantive body + matching scope

Config (environment, OpenAI-compatible /v1/chat/completions):
  LLM_JUDGE_API_KEY   — required for phase 2; missing → unavailable_pass
  LLM_JUDGE_BASE_URL  — default https://api.deepseek.com
  LLM_JUDGE_MODEL     — default deepseek-chat

Usage:
    python .agent-kit/gates/critic_llm_commit.py <path-to-commit-msg-file>

Pre-commit framework wires this as:
    - id: critic_llm_commit
      stages: [commit-msg]
      entry: python .agent-kit/gates/critic_llm_commit.py
      args: [--commit-msg-file]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Closed type/scope vocabularies. Edit here when project rules change.
ALLOWED_TYPES = {
    "feat", "fix", "refactor", "perf", "docs", "test",
    "build", "ci", "chore", "revert",
}
# Generic placeholder scope set — these are EXAMPLES to edit per project.
# Replace with the modules/areas of your own codebase.
ALLOWED_SCOPES = {
    "core", "cli", "api", "ui", "docs", "build", "ci", "deps", "meta",
}
SUBJECT_MAX = 99
# Require a `Tag: vX.Y.Z` trailer on every feat/breaking commit? Off by default for a
# general-purpose kit (most projects don't tag every commit). When present, a Tag: is still
# fully validated (format, collision, SemVer bump). Set True to ENFORCE tagging.
REQUIRE_TAG_TRAILER = False
BODY_REQUIRED_AT_LINES = 50

# Judge endpoint — OpenAI-compatible chat-completions, env-driven.
BASE_URL = os.environ.get("LLM_JUDGE_BASE_URL", "https://api.deepseek.com").rstrip("/")
JUDGE_URL = f"{BASE_URL}/v1/chat/completions"  # /v1 matches critic_llm.py — one URL shape for any OpenAI-compatible host
JUDGE_MODEL = os.environ.get("LLM_JUDGE_MODEL", "deepseek-chat")
TIMEOUT_S = 25


# Subject regex per Conventional Commits 1.0:
#   <type>(<scope>)?<bang>?: <subject>
# Bang goes AFTER the optional scope, BEFORE the colon.
# Examples: `feat: ...`, `feat(core): ...`, `feat!: ...`, `feat(core)!: ...`.
SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z\-]+)\))?(?P<bang>!)?: (?P<subject>.+)$"
)
# Trailer regex: Key: value (per Linux/git trailers)
TRAILER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*: ")
# Strict SemVer Tag: trailer.
TAG_TRAILER_RE = re.compile(r"^Tag:\s*(v\d+\.\d+\.\d+)\s*$", re.MULTILINE)
# Loose Tag: trailer to catch malformed proposals (e.g. `Tag: 3.13.0`,
# `Tag: v3.13`, `Tag: v3.13.0-rc1`) at the commit-msg stage so they get
# flagged as format errors rather than silently ignored.
TAG_TRAILER_LOOSE_RE = re.compile(r"^Tag:\s*(\S+).*$", re.MULTILINE)


def load_api_key() -> str | None:
    k = os.environ.get("LLM_JUDGE_API_KEY", "").strip()
    if k:
        return k
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("LLM_JUDGE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def unavailable_pass(reason: str) -> int:
    print(f"[critic_llm_commit] JUDGE UNAVAILABLE — {reason}", file=sys.stderr)
    return 0


# Sidecars live next to the per-file ones written by critic_llm.py
# (`.llm-review/<encoded-path>.json`). One file per commit invocation,
# named by UTC timestamp so the full history is preserved — every verdict
# stays on disk, including warns that would otherwise be overwritten by a
# subsequent clean commit. List newest with `ls -t .llm-review/_commit_*`.
SIDECAR_DIR = REPO_ROOT / ".llm-review"


def write_sidecar(msg: str, verdict: dict) -> Path | None:
    """Persist verdict + message context. Returns path on success, None
    on failure. A disk-write failure must NOT block the commit — the
    sidecar is a debugging aid, not a gate. Caller falls back to
    stderr-only output when this returns None."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    # Timestamp FIRST in filename so `ls`-sort gives chronological order;
    # `_commit` suffix tags the kind so per-file + audit + commit-msg
    # sidecars in the same dir stay distinguishable.
    path = SIDECAR_DIR / f"{stamp}_commit.json"
    payload = {
        "timestamp_utc": stamp,
        "severity": verdict.get("severity", "ok"),
        "summary": verdict.get("summary", ""),
        "issues": verdict.get("issues", []) or [],
        "commit_message": msg,
    }
    try:
        SIDECAR_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as e:
        print(
            f"[critic_llm_commit] sidecar write failed ({e}); "
            "verdict only on stderr below.",
            file=sys.stderr,
        )
        return None
    return path


def staged_diff() -> str:
    """Return the staged diff (`git diff --cached`)."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--no-color", "--unified=3"],
            capture_output=True, text=True, check=True,
        )
        return r.stdout
    except subprocess.CalledProcessError:
        return ""


def staged_files() -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, check=True,
        )
        return [l.strip() for l in r.stdout.splitlines() if l.strip()]
    except subprocess.CalledProcessError:
        return []


def latest_tag() -> str | None:
    """Return the highest-version SemVer tag (v<int>.<int>.<int>) reachable
    from HEAD, or None if no SemVer tag exists. Ignores non-SemVer tags.
    Sorts numerically by (major, minor, patch) so the result is
    deterministic even when two tags were created in the same second."""
    r = subprocess.run(
        ["git", "tag", "--merged", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0 or r.stdout is None:
        return None
    semver = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
    best: tuple[int, int, int] | None = None
    best_name: str | None = None
    for line in r.stdout.splitlines():
        t = line.strip()
        m = semver.match(t)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if best is None or key > best:
            best = key
            best_name = t
    return best_name


def commits_since_tag(tag: str | None, limit: int = 50) -> list[str]:
    """Return one-line summaries of commits since the given tag (newest
    first), up to `limit`. If tag is None, return the most recent `limit`
    commits on the current branch."""
    rng = f"{tag}..HEAD" if tag else f"HEAD~{limit}..HEAD"
    r = subprocess.run(
        ["git", "log", "--oneline", "--no-decorate", rng],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0:
        return []
    return [l for l in r.stdout.splitlines() if l.strip()][:limit]


def commit_messages_since_tag(tag: str | None, limit: int = 50) -> list[str]:
    """Return full commit messages (subject + body, no SHA) since the given
    tag, newest first, up to `limit`. Used by `required_bump()` to detect
    `BREAKING CHANGE:` footers that don't appear in `--oneline` summaries.
    If tag is None, returns the most recent `limit` commits."""
    rng = f"{tag}..HEAD" if tag else f"HEAD~{limit}..HEAD"
    # `%B` = raw body (subject + body). `%x1e` is ASCII RECORD-SEPARATOR
    # (0x1E) — uncommon in commit text, so a clean split delimiter that
    # survives messages with arbitrary blank lines.
    r = subprocess.run(
        ["git", "log", rng, "--format=%B%x1e"],
        capture_output=True, text=True, check=False,
    )
    if r.returncode != 0 or r.stdout is None:
        return []
    parts = r.stdout.split("\x1e")
    return [p.strip() for p in parts if p.strip()][:limit]


def classify_message(msg: str) -> tuple[str, bool]:
    """Return (commit_type, is_breaking). `commit_type` is the lowercase
    Conventional Commits type (`feat`, `fix`, `docs`, ...) or `"other"` if
    the subject doesn't parse. `is_breaking` is True when the subject has a
    `!:` bang OR the body contains a `BREAKING CHANGE:` / `BREAKING-CHANGE:`
    line."""
    if not msg:
        return ("other", False)
    lines = msg.splitlines()
    first = lines[0] if lines else ""
    m = SUBJECT_RE.match(first)
    t = m.group("type") if m else "other"
    bang = bool(m.group("bang")) if m else False
    breaking_footer = any(
        line.startswith("BREAKING CHANGE:") or line.startswith("BREAKING-CHANGE:")
        for line in lines
    )
    return (t, bang or breaking_footer)


def required_bump(messages: list[str]) -> str:
    """Return 'major' / 'minor' / 'patch' / 'none' for a cumulative commit
    list, applying strict SemVer rules to Conventional Commits types:

    - any breaking change          → 'major'
    - any `feat:`                  → 'minor'
    - any `fix:` / `perf:` / `refactor:` (release-relevant) → 'patch'
    - only `docs:` / `test:` / `chore:` / `build:` / `ci:` / `revert:` → 'none'

    'none' means no SemVer bump is required by the cumulative changes; the
    author may still tag at patch level if they want to mark the milestone,
    but no tag is required.
    """
    has_breaking = False
    has_feat = False
    has_release_relevant = False
    for m in messages:
        t, br = classify_message(m)
        if br:
            has_breaking = True
        if t == "feat":
            has_feat = True
        if t in {"fix", "perf", "refactor"}:
            has_release_relevant = True
    if has_breaking:
        return "major"
    if has_feat:
        return "minor"
    if has_release_relevant:
        return "patch"
    return "none"


def required_next_tag(prev_tag: str | None, bump: str) -> str | None:
    """Return the strict-SemVer string for the required next tag, or None
    when bump is 'none' (no tag required)."""
    if bump == "none":
        return None
    return next_semver_options(prev_tag).get(bump)


def extract_tag_trailer(msg: str) -> tuple[str | None, str | None]:
    """Return (strict_match, loose_match). strict_match is the SemVer value
    if the trailer is well-formed; loose_match is the raw value if the line
    starts with `Tag:` but format is broken (so we can flag it). Both can
    be None if no trailer at all."""
    strict = TAG_TRAILER_RE.search(msg)
    if strict:
        return strict.group(1), strict.group(1)
    # Search every line that starts with `Tag:` to catch malformed proposals.
    for line in msg.splitlines():
        m = TAG_TRAILER_LOOSE_RE.match(line)
        if m:
            return None, m.group(1)
    return None, None


def parse_semver(v: str) -> tuple[int, int, int] | None:
    m = re.match(r"^v(\d+)\.(\d+)\.(\d+)$", v)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def next_semver_options(prev: str | None) -> dict[str, str]:
    """Given the previous strict SemVer tag (or None for first-ever tag),
    return the three valid next bumps as `{"patch": ..., "minor": ..., "major": ...}`.
    Used in the prompt so the AI judge can compare the proposed Tag: against
    the deterministic option set instead of re-deriving SemVer arithmetic."""
    if prev is None:
        return {"patch": "v0.1.0", "minor": "v0.1.0", "major": "v1.0.0"}
    parsed = parse_semver(prev)
    if parsed is None:
        # Previous tag wasn't strict SemVer — start fresh at v1.0.0 / v0.1.0.
        return {"patch": "v1.0.0", "minor": "v1.0.0", "major": "v1.0.0"}
    maj, mn, pt = parsed
    return {
        "patch": f"v{maj}.{mn}.{pt + 1}",
        "minor": f"v{maj}.{mn + 1}.0",
        "major": f"v{maj + 1}.0.0",
    }


def diff_stats(diff: str) -> tuple[int, int, int]:
    """Return (added_lines, removed_lines, files_touched). Cheap parse.

    A file is counted exactly once on its `+++ b/<path>` header line.
    `---` headers are skipped (source side; would double-count).
    """
    added = removed = files = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            files += 1
        elif line.startswith("---"):
            continue  # source-side header; the `+++ b/` line counts the file
        elif line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed, files


def validate_format(msg: str) -> list[tuple[str, str]]:
    """Return list of (severity, message). 'block' or 'warn'."""
    errors: list[tuple[str, str]] = []
    lines = msg.splitlines()
    if not lines:
        return [("block", "empty commit message")]

    subject = lines[0]
    m = SUBJECT_RE.match(subject)
    if not m:
        return [("block",
                 f"subject does not match Conventional Commits format "
                 f"`<type>(<scope>)?!?: <subject>`. Got: {subject!r}")]

    t = m.group("type")
    scope = m.group("scope")
    subj_text = m.group("subject")
    if t not in ALLOWED_TYPES:
        errors.append(("block",
                       f"type {t!r} not in allowed set: {sorted(ALLOWED_TYPES)}"))
    if scope and scope not in ALLOWED_SCOPES:
        errors.append(("block",
                       f"scope ({scope}) not in allowed set: {sorted(ALLOWED_SCOPES)}"))
    if len(subject) > SUBJECT_MAX:
        errors.append(("block",
                       f"subject {len(subject)} chars > {SUBJECT_MAX} max"))
    if subj_text.endswith("."):
        errors.append(("warn", "subject should not end with `.`"))
    # Imperative mood heuristic
    bad_starters = {"added", "adds", "fixed", "fixes", "updated", "removed"}
    first_word = subj_text.split()[0].lower() if subj_text.split() else ""
    if first_word in bad_starters:
        errors.append(("warn",
                       f"subject not imperative mood (starts with {first_word!r}); "
                       f"use 'add'/'fix'/'update' not '-ed'/'-s' form"))

    # Body check: if more than 1 line, line 2 must be blank
    if len(lines) > 1 and lines[1].strip() != "":
        errors.append(("block",
                       "no blank line between subject and body"))

    # Body-required check: a substantial diff needs a rationale body. The
    # caller decides the threshold (BODY_REQUIRED_AT_LINES); the body
    # adequacy vs the diff is cross-checked by the LLM phase.
    # (Format phase only enforces the structural blank-line rule above.)

    # Tag: trailer checks. The full chain runs deterministically here so
    # the AI judge never has to do SemVer arithmetic (it gets that wrong).
    # Four layers:
    #   0. requirement — `feat:` and any BREAKING commit MUST carry a Tag:
    #      trailer.
    #   1. format — strict `v<int>.<int>.<int>` (no suffixes, no metadata)
    #   2. collision — tag must not already exist in the repo
    #   3. bump correctness — value must match the SemVer bump dictated by
    #      the cumulative commit set since the last strict-SemVer tag,
    #      including this in-flight commit's message
    strict, loose = extract_tag_trailer(msg)
    this_type, this_breaking = classify_message(msg)
    if REQUIRE_TAG_TRAILER and (this_type == "feat" or this_breaking) and strict is None and loose is None:
        # Layer 0: trailer required. Compute the expected value so the
        # error message tells the author exactly what to paste.
        last = latest_tag()
        cumulative = [msg] + commit_messages_since_tag(last)
        expected_bump = required_bump(cumulative)
        expected_tag = next_semver_options(last).get(expected_bump, "vX.Y.Z")
        label = f"{this_type}{'!' if this_breaking else ''}"
        errors.append((
            "block",
            f"`{label}:` commits require a `Tag: vX.Y.Z` trailer. "
            f"Cumulative bump from {last or '(no prior tag)'} = "
            f"`{expected_bump}` → append `Tag: {expected_tag}` to the "
            f"message body and re-commit. Other types "
            f"(fix/refactor/perf/docs/test/chore/build/ci/revert) stay "
            f"optional.",
        ))
    if loose and strict is None:
        errors.append((
            "block",
            f"malformed `Tag:` trailer (got {loose!r}); expected strict "
            f"SemVer `Tag: vX.Y.Z` (no suffixes, no metadata)",
        ))
    elif strict is not None:
        # Layer 2: collision check.
        r = subprocess.run(
            ["git", "rev-parse", "--verify", f"{strict}^{{commit}}"],
            capture_output=True, text=True, check=False,
        )
        if r.returncode == 0:
            errors.append((
                "block",
                f"`Tag: {strict}` already exists in this repo at "
                f"{r.stdout.strip()[:10]}; pick a higher version or drop "
                f"the trailer",
            ))
        else:
            # Layer 3: bump correctness. Cumulative = (in-flight msg) +
            # (commits since last strict-SemVer tag). The in-flight commit's
            # message lives in `msg` because we're at commit-msg stage —
            # HEAD doesn't include it yet.
            last = latest_tag()
            cumulative = [msg] + commit_messages_since_tag(last)
            bump = required_bump(cumulative)
            options = next_semver_options(last)
            # 'none' (only docs/chore/etc cumulative) — patch is the only
            # value the author may legitimately propose (release-irrelevant
            # types don't justify minor or major).
            allowed = (
                {options["patch"]} if bump == "none"
                else {options[bump]}
            )
            if strict not in allowed:
                # Build a "why" string from cumulative for the error message.
                types_seen = []
                for cm in cumulative:
                    ct, cbr = classify_message(cm)
                    label = f"{ct}!" if cbr else ct
                    types_seen.append(label)
                want = ", ".join(sorted(allowed))
                errors.append((
                    "block",
                    f"`Tag: {strict}` does not match required SemVer bump. "
                    f"Cumulative since {last or '(no prior tag)'} contains "
                    f"{len(cumulative)} commit(s) with types "
                    f"[{', '.join(types_seen)}] — required bump is "
                    f"`{bump}` → expected `Tag: {want}`. "
                    f"(Bump rule: any `BREAKING CHANGE:`/`!:` → major; "
                    f"any `feat:` → minor; any `fix:`/`perf:`/`refactor:` → "
                    f"patch; otherwise no tag required.)",
                ))

    return errors


_FALLBACK_COMMIT_TEMPLATE = "Conventional Commits reviewer. Allowed types __ALLOWED_TYPES__, scopes __ALLOWED_SCOPES__. Cross-check the message against the diff (format + SemVer already validated in code; do not re-check). BLOCK on type-vs-diff mismatch, scope-vs-paths mismatch, or a large diff over ~50 lines with an empty or filler body. MESSAGE: __MSG__ || FILES __FILE_COUNT__ (+__ADDED__/-__REMOVED__): __FILES_BLOCK__ || DIFF: __DIFF_EXCERPT__ || Return strict JSON: severity (ok|warn|block), summary, issues (list of severity/category/message/fix). Omit non-issues."


def _load_commit_prompt_template() -> str:
    """Load the editable commit-judge prompt template; fall back inline."""
    p = Path(__file__).resolve().parent / "prompts" / "critic_llm_commit.md"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return _FALLBACK_COMMIT_TEMPLATE


def build_judge_prompt(msg: str, diff: str, files: list[str]) -> str:
    added, removed, file_count = diff_stats(diff)
    diff_excerpt = diff[:8000] if len(diff) > 8000 else diff
    files_block = "\n".join(f"- {f}" for f in files[:20])
    if len(files) > 20:
        files_block += f"\n... ({len(files) - 20} more)"

    tmpl = _load_commit_prompt_template()
    return (
        tmpl.replace("__ALLOWED_TYPES__", str(sorted(ALLOWED_TYPES)))
        .replace("__ALLOWED_SCOPES__", str(sorted(ALLOWED_SCOPES)))
        .replace("__MSG__", msg)
        .replace("__FILE_COUNT__", str(file_count))
        .replace("__ADDED__", str(added))
        .replace("__REMOVED__", str(removed))
        .replace("__FILES_BLOCK__", files_block)
        .replace("__DIFF_EXCERPT__", diff_excerpt)
    )


def call_judge(prompt: str, api_key: str) -> dict | None:
    body = json.dumps({
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        JUDGE_URL,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, TimeoutError):
        return None


# An LLM judge sometimes tags a PASSING observation `severity: "block"`
# with a `fix` of "No fix needed." / "satisfied" / "" — a passing check
# mislabelled. A genuine block MUST carry a concrete, actionable fix; a
# "block" issue whose `fix` is empty or a no-op phrase is not a real
# blocker. The prompt tells the model not to emit these, but the model is
# non-deterministic — this is the script-side backstop so a no-fix "block"
# cannot abort a commit.
_NON_FIX_RE = re.compile(
    r"^(no fix needed|no fix|none|n/?a|satisfied|no hard block|no issue"
    r"|no change(s)? needed|accept.*|ok)\.?$",
    re.IGNORECASE,
)


def issue_is_actionable_block(issue: dict) -> bool:
    """True iff `issue` is a `block` carrying a concrete fix. A `block`
    issue whose `fix` is empty or a no-op phrase ('No fix needed.') is
    NOT actionable and must not abort the commit."""
    if (issue.get("severity") or "").lower() != "block":
        return False
    fix = (issue.get("fix") or "").strip()
    return bool(fix) and _NON_FIX_RE.match(fix) is None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("commit_msg_file", help="Path to .git/COMMIT_EDITMSG (provided by git)")
    ap.add_argument("--no-judge", action="store_true",
                    help="Skip LLM call (format check only)")
    args = ap.parse_args()

    msg_path = Path(args.commit_msg_file)
    if not msg_path.exists():
        print(f"[critic_llm_commit] BLOCK — message file not found: {msg_path}",
              file=sys.stderr)
        return 1

    # Strip git's commented lines (starting with #) and trailing whitespace
    raw = msg_path.read_text(encoding="utf-8")
    lines = [l for l in raw.splitlines() if not l.startswith("#")]
    msg = "\n".join(lines).strip()
    if not msg:
        print("[critic_llm_commit] BLOCK — empty commit message", file=sys.stderr)
        return 1

    # Phase 1: deterministic format check (always runs)
    fmt_errors = validate_format(msg)
    blocks = [e for e in fmt_errors if e[0] == "block"]
    warns = [e for e in fmt_errors if e[0] == "warn"]

    if blocks:
        print("[critic_llm_commit] BLOCK on format:", file=sys.stderr)
        for sev, m in blocks + warns:
            print(f"  [{sev.upper()}] {m}", file=sys.stderr)
        print(f"\n  Conventional Commits format:\n  <type>(<scope>)?!?: <subject ≤{SUBJECT_MAX} chars>\n\n  <body — explain WHY>\n\n  <trailers>\n  Tag: vX.Y.Z   (required on feat/breaking)\n  Closes #N\n", file=sys.stderr)
        return 1

    if warns:
        print("[critic_llm_commit] format warnings (non-blocking):", file=sys.stderr)
        for sev, m in warns:
            print(f"  [{sev.upper()}] {m}", file=sys.stderr)

    # Phase 2: LLM judge
    if args.no_judge:
        return 0

    api_key = load_api_key()
    if not api_key:
        return unavailable_pass("LLM_JUDGE_API_KEY not set")

    diff = staged_diff()
    files = staged_files()
    if not diff:
        # Nothing staged — likely an `--amend` of an empty commit, or other
        # edge case. Format check passed; we can't judge content.
        return 0

    prompt = build_judge_prompt(msg, diff, files)
    verdict = call_judge(prompt, api_key)
    if verdict is None:
        return unavailable_pass("judge call failed (network / API)")

    summary = verdict.get("summary", "")
    issues = verdict.get("issues", []) or []
    # Derive overall severity from the issues array rather than trusting
    # the model's top-level `severity` field. Two model misbehaviours are
    # corrected here:
    #   - top-level `severity: "block"` while every `issues` entry is
    #     `warn` — "block with no actionable items".
    #   - `issues` entries tagged `severity: "block"` whose `fix` is
    #     "No fix needed." — a passing check mislabelled.
    # The gate's job is to block on CONCRETE blockers only: a commit blocks
    # iff at least one issue is a block carrying an actionable fix
    # (issue_is_actionable_block). A block issue with no real fix is
    # downgraded to a non-blocking warn so it still surfaces.
    if any(issue_is_actionable_block(i) for i in issues):
        severity = "block"
    elif issues:
        severity = "warn"  # warn-level or no-fix blocks → surface, don't abort
    else:
        # Empty issues list → trust the model's overall severity.
        severity = verdict.get("severity", "ok")

    sidecar = write_sidecar(msg, verdict)
    rel = sidecar.relative_to(REPO_ROOT).as_posix() if sidecar else None

    if severity == "ok":
        # Print on ok too — otherwise a clean pass is indistinguishable
        # from "the judge never ran." The sidecar bytes prove the judge ran.
        n = len(issues)
        suffix = f" ({n} non-blocking note{'s' if n != 1 else ''})" if n else ""
        link = f". Full verdict: {rel}" if rel else " (sidecar unwritable)"
        print(
            f"[critic_llm_commit] OK — {summary or 'message validated'}"
            f"{suffix}{link}",
            file=sys.stderr,
        )
        return 0

    label = "BLOCK" if severity == "block" else "WARN "
    print(f"\n[critic_llm_commit] {label} — {summary}", file=sys.stderr)
    for issue in issues:
        raw_sev = (issue.get("severity") or severity).lower()
        # A `block` issue with no actionable fix was downgraded above;
        # print it as WARN so the line matches the (non-blocking) verdict.
        if raw_sev == "block" and not issue_is_actionable_block(issue):
            sev = "WARN"
        else:
            sev = raw_sev.upper()
        cat = issue.get("category", "other")
        m = issue.get("message", "")
        fix = issue.get("fix", "")
        print(f"  [{sev}] ({cat}) {m}", file=sys.stderr)
        if fix:
            print(f"       fix: {fix}", file=sys.stderr)
    if rel:
        print(f"  Full verdict (JSON): {rel}", file=sys.stderr)

    if severity == "block":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
