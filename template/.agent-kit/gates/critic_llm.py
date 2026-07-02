#!/usr/bin/env python3
# USER-AUTHORIZED 2026-04-29: unavailable_pass behavior — when
# LLM_JUDGE_API_KEY is missing, the judge endpoint is unreachable, or
# a per-file call fails after one retry, the gate exits 0 with a stderr
# warning and the commit proceeds. The AI judge is best-effort, not a
# hard gate; an offline day still ships. NOT a banned bypass flag — no
# user toggle, fires only on a verifiable provider-outage condition.
# REASON: Language-agnostic AI code critic — sends each staged text/source file
# (full content + staged diff) to an OpenAI-compatible chat-completions endpoint,
# parses a strict-JSON verdict, and prepends an LLM_REVIEW_BLOCK header to the
# file when severity=block/warn so the finding survives stderr truncation. It
# sidecar-caches verdicts by sha256 of clean content (.llm-review/<path>.json) so
# a file is re-reviewed only when it actually changes, instead of on every commit.
# Implements `unavailable_pass` (rc=0 + stderr warning) when LLM_JUDGE_API_KEY is
# missing, the endpoint is unreachable, or a per-file call fails after one retry —
# USER-AUTHORIZED 2026-04-29, see top-of-file authorization line. Also reused via
# `--files <path> --no-mutate` by the .agent-kit/adapters/claude/hooks/check-script-launch.py
# PreToolUse hook for ad-hoc launch-time review (working-tree, no block mutation).
""".agent-kit/gates/critic_llm.py — AI-judge pre-commit gate (any language).

Per-file flow:
  1. read staged content (`git show :path`) and staged diff (`git diff --cached`)
  2. strip any prior LLM_REVIEW_BLOCK comment, sha256 the clean content
  3. cache lookup at .llm-review/<encoded-path>.json — sha match → reuse
  4. otherwise: POST to the configured judge model with rubric + full file + diff
  5. parse {severity, summary, issues[]}; write sidecar; ingest LLM_REVIEW_BLOCK
     into the WORKING TREE file when severity != ok.

Severity:
  - ok    → no comment, sidecar deleted, LLM_REVIEW_BLOCK stripped if present.
  - warn  → LLM_REVIEW_BLOCK prepended; commit allowed.
  - block → LLM_REVIEW_BLOCK prepended; commit BLOCKED (exit 1).

unavailable_pass path: if LLM_JUDGE_API_KEY missing, endpoint down, or any
per-file call fails after one retry, the gate emits a one-line stderr warning
and exits 0. The AI judge is best-effort — an offline day or provider outage
still ships commits. There is no deterministic fallback.

Config (environment, OpenAI-compatible /chat/completions):
  LLM_JUDGE_API_KEY   — required; missing → unavailable_pass
  LLM_JUDGE_BASE_URL  — default https://api.deepseek.com
  LLM_JUDGE_MODEL     — default deepseek-chat

Exit codes:
  0 — all files ok or warn, OR judge unavailable (unavailable-pass)
  1 — at least one block (commit blocked)
  2 — internal error (sub-call setup failed)

CLI:
  python .agent-kit/gates/critic_llm.py            # gate mode (review staged set)
  python .agent-kit/gates/critic_llm.py --files A B  # ad-hoc, review named files
  python .agent-kit/gates/critic_llm.py --dry-run   # show staged set, no API call
  python .agent-kit/gates/critic_llm.py --no-mutate  # don't write LLM_REVIEW_BLOCK
                                                  # into files (used by the
                                                  # PreToolUse launch-time hook)
  python .agent-kit/gates/critic_llm.py --json      # machine-readable summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Config — OpenAI-compatible chat-completions endpoint, env-driven.
# All three judge settings (KEY, BASE_URL, MODEL) fall back to the repo .env,
# so the recommended put-everything-in-.env path actually works (issue #5:
# env-only BASE_URL/MODEL made an NVIDIA judge silently soft-pass against the
# DeepSeek default URL).
# ---------------------------------------------------------------------------


def _dotenv_get(name: str) -> str | None:
    env = REPO_ROOT / ".env"
    if not env.exists():
        return None
    for line in env.read_text(encoding="utf-8").splitlines():
        if line.startswith(name + "="):
            v = line.split("=", 1)[1].strip()
            if v.startswith(("'", '"')) and v.endswith(("'", '"')):
                v = v[1:-1]
            return v or None
    return None


def _cfg(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, "").strip()
    return v or _dotenv_get(name) or default


BASE_URL = _cfg("LLM_JUDGE_BASE_URL", "https://api.deepseek.com").rstrip("/")
API_URL = f"{BASE_URL}/v1/chat/completions"
MODEL = _cfg("LLM_JUDGE_MODEL", "deepseek-chat")

# Files we review. Generic source/text set — edit to fit your project.
SUPPORTED_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb", ".java",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cs", ".php", ".sh", ".bash",
    ".sql", ".kt", ".swift", ".scala", ".lua", ".pl",
}
SIDECAR_DIR = REPO_ROOT / ".llm-review"

# Per-call API timeout. Cold calls on a large file can take ~10s; allow
# generous slack for tail latency without making the gate hang the commit.
API_CALL_TIMEOUT_S = 90
HEALTH_CHECK_TIMEOUT_S = 3

# Concurrency cap. Most providers tolerate parallel calls; default 8 for the
# normal commit path (rate-limit headroom on 20+ file mega-commits). Override
# via CRITIC_LLM_MAX_PARALLEL for one-shot full-repo audit runs.
MAX_PARALLEL_CALLS = int(os.environ.get("CRITIC_LLM_MAX_PARALLEL", "8"))

# Hard byte cap on file size — anything bigger is skipped with a notice
# (the rubric is wasted on huge blobs and the response is unreliable).
MAX_FILE_BYTES = 200_000

# Marker the LLM_REVIEW_BLOCK header starts with. Used both to identify and
# to strip prior blocks before re-review.
BLOCK_MARKER = "=== LLM_REVIEW_BLOCK"
END_MARKER = "=== END_LLM_REVIEW_BLOCK ==="

# ---------------------------------------------------------------------------
# System rubric — sent on every call, fully cache-stable. Providers that
# support automatic prompt caching hit ~99% of this prompt after the first
# call, so the rubric portion costs near zero on subsequent calls.
# ---------------------------------------------------------------------------

def _load_prompt(filename: str, fallback: str) -> str:
    """Load an editable prompt from the prompts/ dir next to this script.
    Falls back to a compact inline rubric if the file is missing so the gate
    still functions even if the prompts dir is deleted."""
    p = Path(__file__).resolve().parent / "prompts" / filename
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return fallback


_FALLBACK_RUBRIC = "Senior code-review judge. Review the staged diff (full file for context), any language, for: correctness/logic bugs, swallowed errors, hardcoded secrets/injection, over-engineering, duplication, obvious performance (IO/DB/HTTP in loops, O(n^2) on large N), dead code/TODOs. Return strict JSON with keys severity (ok|warn|block), summary, and issues (a list of objects with line, severity, category, issue, fix). Block only on real correctness/security defects; warn on quality; default ok when uncertain."

SYSTEM_RUBRIC = _load_prompt("critic_llm.md", _FALLBACK_RUBRIC)

# PROJECT CONTEXT — what this project is, its domain rules, its critical invariants. Written by the
# /setup-pravda-skills interview (or by hand) to gates/prompts/project-context.md. Without it the judge
# reviews in a vacuum and misses domain-specific danger (the generic rubric cannot know a trading bot's
# order-safety rules from a blog's content rules). Appended so the rubric stays generic and upgradeable.
_PROJECT_CONTEXT = _load_prompt("project-context.md", "")
if _PROJECT_CONTEXT.strip():
    SYSTEM_RUBRIC = SYSTEM_RUBRIC + "\n\n## PROJECT CONTEXT (weigh every finding against this)\n" + _PROJECT_CONTEXT


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class Verdict:
    severity: str  # "ok" | "warn" | "block"
    summary: str
    issues: list[dict] = field(default_factory=list)
    sha: str = ""
    cached: bool = False  # True when reused from sidecar
    error: str | None = None  # set on per-file API failure

    @classmethod
    def ok(cls, sha: str = "") -> "Verdict":
        return cls(severity="ok", summary="", issues=[], sha=sha)

    @classmethod
    def errored(cls, msg: str) -> "Verdict":
        return cls(severity="ok", summary="", issues=[], error=msg)


# ---------------------------------------------------------------------------
# stderr helper — we never write to stdout from the gate; the dispatcher
# captures stderr and forwards it under the gate banner.
# ---------------------------------------------------------------------------


def eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


# The kit's own vendored machinery is reviewed in the kit's repo, not in every
# adopting repo — judging it here produces noise verdicts on battle-tested files
# on the very first adoption commit (same self-exemption precedent as
# check_md_size). Derived from __file__ so a --kit-name rename still works.
_KIT_DIR_NAME = Path(__file__).resolve().parents[1].name
_EXEMPT_PREFIXES = ((_KIT_DIR_NAME,), (".claude", "skills"), (".agents", "skills"))


def _is_kit_vendored(p: Path) -> bool:
    """True for paths inside the kit's own dir or a vendored skills mirror."""
    return any(p.parts[: len(pre)] == pre for pre in _EXEMPT_PREFIXES)


def get_staged_source_files() -> list[Path]:
    """Return staged paths under SUPPORTED_EXTS, relative to repo root."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    out: list[Path] = []
    for line in proc.stdout.splitlines():
        s = line.strip()
        if not s:
            continue
        p = Path(s)
        if p.suffix in SUPPORTED_EXTS and not _is_kit_vendored(p):
            out.append(p)
    return out


def get_staged_content(path: Path) -> str | None:
    """Return staged version of `path` (`git show :path`); None if unreadable."""
    proc = subprocess.run(
        ["git", "show", f":{path.as_posix()}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def get_staged_diff(path: Path) -> str:
    """Return the unified staged diff for `path`."""
    proc = subprocess.run(
        ["git", "diff", "--cached", "--", path.as_posix()],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


# ---------------------------------------------------------------------------
# LLM_REVIEW_BLOCK insert / strip
# ---------------------------------------------------------------------------

# Languages whose line comment is `//` rather than `#`. Everything else
# defaults to `#` (Python, shell, Ruby, SQL `--` is rare; `#` is the safe
# default for the prepended header block).
_SLASH_COMMENT_EXTS = {
    ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".h",
    ".cc", ".cpp", ".hpp", ".cs", ".php", ".kt", ".swift", ".scala",
}


def comment_char_for(path: Path) -> str:
    return "//" if path.suffix in _SLASH_COMMENT_EXTS else "#"


def review_block_text(verdict: Verdict, cc: str) -> str:
    """Build the multi-line LLM_REVIEW_BLOCK comment that gets prepended."""
    lines = [
        f"{cc} {BLOCK_MARKER} severity={verdict.severity} model={MODEL} ===",
        f"{cc} Summary: {verdict.summary}",
    ]
    for i, issue in enumerate(verdict.issues, 1):
        line_no = issue.get("line", "?")
        sev = issue.get("severity", "?")
        category = issue.get("category", "?")
        text = issue.get("issue", "")
        fix = issue.get("fix", "")
        lines.append(f"{cc} {i}. L{line_no} ({sev}, {category}): {text} -> {fix}")
    lines.append(
        f"{cc} Address each item, remove this entire block, re-stage, re-commit."
    )
    lines.append(f"{cc} {END_MARKER}")
    return "\n".join(lines) + "\n"


def insert_review_block(content: str, block: str) -> str:
    """Prepend `block` to `content`, after a shebang line if present."""
    if content.startswith("#!"):
        nl = content.find("\n")
        if nl == -1:
            return content + "\n" + block
        return content[: nl + 1] + block + content[nl + 1 :]
    return block + content


_BLOCK_RE = re.compile(
    r"^(#|//) " + re.escape(BLOCK_MARKER) + r"[^\n]*\n"
    r"(?:[^\n]*\n)*?"
    r"\1 " + re.escape(END_MARKER) + r"\n",
)


def strip_review_block(content: str) -> str:
    """Remove an existing LLM_REVIEW_BLOCK from `content`, if present.

    Handles a leading shebang correctly: the block sits between the shebang
    and the rest of the file."""
    prefix = ""
    body = content
    if content.startswith("#!"):
        nl = content.find("\n")
        if nl != -1:
            prefix = content[: nl + 1]
            body = content[nl + 1 :]
    m = _BLOCK_RE.match(body)
    if m:
        body = body[m.end() :]
    return prefix + body


def apply_review_block(path: Path, verdict: Verdict) -> None:
    """Write LLM_REVIEW_BLOCK into the working-tree file (replacing any prior)."""
    full = REPO_ROOT / path
    if not full.exists():
        return
    content = full.read_text(encoding="utf-8")
    cleaned = strip_review_block(content)
    cc = comment_char_for(path)
    block = review_block_text(verdict, cc)
    new_content = insert_review_block(cleaned, block)
    if new_content != content:
        full.write_text(new_content, encoding="utf-8")


def remove_review_block(path: Path) -> None:
    """Strip LLM_REVIEW_BLOCK from working-tree file if present."""
    full = REPO_ROOT / path
    if not full.exists():
        return
    content = full.read_text(encoding="utf-8")
    cleaned = strip_review_block(content)
    if cleaned != content:
        full.write_text(cleaned, encoding="utf-8")


# ---------------------------------------------------------------------------
# API key + health check
# ---------------------------------------------------------------------------


def get_api_key() -> str | None:
    """Read LLM_JUDGE_API_KEY from env or .env (in that order). None if missing."""
    return _cfg("LLM_JUDGE_API_KEY")


def judge_health_check() -> bool:
    """Quick TCP-level reachability test against the judge host:port.

    Cheap (no API call, no key needed). Three-second timeout. Host and port
    are derived from LLM_JUDGE_BASE_URL."""
    parsed = urllib.parse.urlparse(BASE_URL)
    host = parsed.hostname or "api.deepseek.com"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=HEALTH_CHECK_TIMEOUT_S):
            return True
    except (OSError, TimeoutError):
        return False


# ---------------------------------------------------------------------------
# Sidecar cache
# ---------------------------------------------------------------------------


def sidecar_path_for(path: Path) -> Path:
    safe = path.as_posix().replace("/", "__")
    return SIDECAR_DIR / f"{safe}.json"


def load_sidecar(path: Path, sha: str) -> Verdict | None:
    sc = sidecar_path_for(path)
    if not sc.exists():
        return None
    try:
        data = json.loads(sc.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if data.get("sha") != sha:
        return None
    return Verdict(
        severity=data.get("severity", "ok"),
        summary=data.get("summary", ""),
        issues=data.get("issues", []),
        sha=sha,
        cached=True,
    )


def save_sidecar(path: Path, verdict: Verdict) -> None:
    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)
    sc = sidecar_path_for(path)
    sc.write_text(
        json.dumps(
            {
                "path": path.as_posix(),
                "sha": verdict.sha,
                "severity": verdict.severity,
                "summary": verdict.summary,
                "issues": verdict.issues,
                "model": MODEL,
                "ts": time.time(),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Single API call
# ---------------------------------------------------------------------------


def _post_once(messages: list[dict], api_key: str) -> dict:
    body = json.dumps(
        {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=API_CALL_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode("utf-8"))


def call_judge(path: Path, content: str, diff: str, api_key: str) -> Verdict:
    """One review call with one retry on transient failure. Raises on second fail."""
    user_msg = (
        f"File: {path.as_posix()}\n\n"
        f"=== FULL CONTENT ===\n{content}\n\n"
        f"=== STAGED DIFF ===\n{diff if diff else '(empty diff)'}\n\n"
        "Review per the rubric. Strict JSON only."
    )
    messages = [
        {"role": "system", "content": SYSTEM_RUBRIC},
        {"role": "user", "content": user_msg},
    ]

    for attempt in (1, 2):
        try:
            data = _post_once(messages, api_key)
            break
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == 1:
                # one-shot cooldown between two API attempts; fixed 1s, no event to await
                time.sleep(1.0)
            else:
                raise RuntimeError(f"judge API call failed twice for {path}: {e}") from e

    raw = data["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        eprint(f"[critic_llm] {path}: model returned non-JSON, treating as ok: {raw[:200]}")
        return Verdict.ok()

    sev = parsed.get("severity", "ok")
    if sev not in ("ok", "warn", "block"):
        sev = "ok"
    return Verdict(
        severity=sev,
        summary=str(parsed.get("summary", ""))[:200],
        issues=list(parsed.get("issues", []) or [])[:50],
    )


# ---------------------------------------------------------------------------
# Per-file review entry point
# ---------------------------------------------------------------------------


def review_file(path: Path, api_key: str, source: str = "staged") -> Verdict:
    """Review one file. Uses sidecar cache. Raises on API failure.

    source = "staged" → read via `git show :path` and `git diff --cached`.
    source = "worktree" → read working-tree file (ad-hoc / smoke-test mode);
    diff = full content as a single +-block."""
    if source == "staged":
        raw = get_staged_content(path)
        if raw is None:
            return Verdict.errored("could not read staged content")
        diff = get_staged_diff(path)
    else:
        full = REPO_ROOT / path
        if not full.exists():
            return Verdict.errored("file not found")
        raw = full.read_text(encoding="utf-8")
        diff = "(reviewing working tree; full file shown above is the diff)"

    cleaned = strip_review_block(raw)
    sha = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()

    cached = load_sidecar(path, sha)
    if cached is not None:
        return cached

    if len(cleaned.encode("utf-8")) > MAX_FILE_BYTES:
        eprint(f"[critic_llm] {path}: file > {MAX_FILE_BYTES} bytes, skipping AI review")
        return Verdict.errored(f"file too large ({len(cleaned)} bytes)")

    verdict = call_judge(path, cleaned, diff, api_key)
    verdict.sha = sha
    save_sidecar(path, verdict)
    return verdict


# ---------------------------------------------------------------------------
# unavailable_pass helper
# ---------------------------------------------------------------------------


def unavailable_pass(reason: str) -> int:
    """Emit a one-line stderr warning + return 0 (commit / launch proceeds)."""
    eprint(f"[critic_llm] AI review SKIPPED — {reason}; passing soft.")
    return 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def render_block(path: Path, verdict: Verdict) -> str:
    head = f"  [{verdict.severity.upper()}] {path}: {verdict.summary}"
    body_lines: list[str] = []
    for i, iss in enumerate(verdict.issues, 1):
        body_lines.append(
            f"      {i}. L{iss.get('line','?')} ({iss.get('severity','?')}, "
            f"{iss.get('category','?')}): {iss.get('issue','')} -> {iss.get('fix','')}"
        )
    return head + ("\n" + "\n".join(body_lines) if body_lines else "")


def emit_report(verdicts: dict[Path, Verdict], elapsed_s: float) -> None:
    blocks = [(p, v) for p, v in verdicts.items() if v.severity == "block"]
    warns = [(p, v) for p, v in verdicts.items() if v.severity == "warn"]
    oks = [(p, v) for p, v in verdicts.items() if v.severity == "ok"]
    cached_n = sum(1 for v in verdicts.values() if v.cached)

    eprint("")
    eprint(f"=== critic_llm ({MODEL}) — {len(verdicts)} files in {elapsed_s:.1f}s, "
           f"{cached_n} from cache ===")
    if blocks:
        eprint(f"\n  {len(blocks)} BLOCK(s):")
        for p, v in blocks:
            eprint(render_block(p, v))
    if warns:
        eprint(f"\n  {len(warns)} WARN(s):")
        for p, v in warns:
            eprint(render_block(p, v))
    if oks and not (blocks or warns):
        eprint(f"  {len(oks)} OK")

    if blocks:
        eprint("")
        eprint("  Each blocked file has an LLM_REVIEW_BLOCK header prepended in the working tree.")
        eprint("  Read it, address each item, remove the block, re-stage, re-commit.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Review specific files instead of the staged set (ad-hoc mode).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the files that would be reviewed; make no API call.",
    )
    parser.add_argument(
        "--no-mutate",
        action="store_true",
        help="Don't write LLM_REVIEW_BLOCK headers into files (used by the launch-time hook).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single-line JSON summary on stdout.",
    )
    args = parser.parse_args()

    if args.files:
        targets = [Path(f).resolve().relative_to(REPO_ROOT) for f in args.files]
        source_mode = "worktree"
    else:
        targets = get_staged_source_files()
        source_mode = "staged"

    if not targets:
        return 0

    if args.dry_run:
        eprint(f"[critic_llm] dry-run: would review {len(targets)} file(s)")
        for p in targets:
            eprint(f"  - {p}")
        return 0

    api_key = get_api_key()
    if not api_key:
        return unavailable_pass("LLM_JUDGE_API_KEY not set")

    if not judge_health_check():
        return unavailable_pass(f"{BASE_URL} unreachable")

    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.monotonic()
    verdicts: dict[Path, Verdict] = {}
    workers = min(MAX_PARALLEL_CALLS, max(1, len(targets)))
    api_failed = False
    failure_msg = ""
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(review_file, p, api_key, source_mode): p for p in targets}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                verdicts[p] = fut.result()
            except RuntimeError as e:
                api_failed = True
                failure_msg = str(e)
                break
    elapsed = time.monotonic() - t0

    if api_failed:
        return unavailable_pass(f"api call failed: {failure_msg}")

    if not args.no_mutate:
        for p, v in verdicts.items():
            if v.error is not None:
                continue
            if v.severity == "ok":
                remove_review_block(p)
            else:
                apply_review_block(p, v)

    emit_report(verdicts, elapsed)

    if args.json:
        print(
            json.dumps(
                {
                    "model": MODEL,
                    "elapsed_s": round(elapsed, 2),
                    "verdicts": {
                        p.as_posix(): {
                            "severity": v.severity,
                            "summary": v.summary,
                            "issues": v.issues,
                            "cached": v.cached,
                        }
                        for p, v in verdicts.items()
                    },
                }
            )
        )

    has_block = any(v.severity == "block" for v in verdicts.values())
    return 1 if has_block else 0


if __name__ == "__main__":
    sys.exit(main())
