#!/usr/bin/env python3
# REASON: Pre-commit secret gate that scans STAGED TEXT (`git diff --cached`) for
# secret-shaped strings instead of the compiled-binary scan it is modelled on — most
# leaks enter as a source literal before they ever reach a build artifact, so
# scanning the staged diff catches them one layer earlier and works in any language
# with no `strings`/binutils dependency. It blocks the commit on the first added line
# matching a known secret shape (private-key PEM header, hex private key, AWS AKIA,
# GitHub PAT, OpenAI sk-, 1Password ops_eyJ, generic api_key/secret assignment) and
# reports file:line, allowing a per-line escape only via an inline `# SECRET_OK:
# <reason>` comment so each exception is a deliberate, reviewable decision.
"""Pre-commit gate: scan staged TEXT for secret-shaped strings.

Runs every commit. Reads the staged diff (`git diff --cached`) and checks
each ADDED line (the `+` lines, source side excluded) against a documented
pattern set. Reports per-file `file:line` hits, exits 1 if any hit, exits 0
when the staged set is clean.

Why staged text (not compiled binaries): a leaked credential almost always
enters the tree as a source literal first. Catching it at the diff stage
stops it before it is committed, and needs no `strings`/binutils — it works
the same on every OS and for every language.

Allowlist: a real public value or an unavoidable false positive can be
exempted by putting an inline `# SECRET_OK: <reason>` comment on the SAME
added line (the `<reason>` must be at least 30 characters so the exemption
documents itself). This is a deliberate, per-line, reviewable decision —
not a global bypass. The right fix on a real hit is to remove the literal
from source and rotate the credential, not to allowlist it.

Exit codes:
  0 — no staged secret-shaped strings (or every hit is `SECRET_OK`-annotated)
  1 — at least one un-annotated secret-shaped string in the staged diff
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

# Secret-shaped patterns. Modelled on the binary-secrets token list, plus
# PEM private-key headers and generic assignment shapes for staged text.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private-key PEM header",
     re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----")),
    ("hex private key (64 hex chars)", re.compile(r"0x[0-9a-fA-F]{64}")),
    ("AWS access key ID", re.compile(r"AKIA[A-Z0-9]{16}")),
    ("GitHub token", re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    ("OpenAI sk- API token", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    # Real 1Password Service Account tokens begin `ops_eyJ` (base64 JSON);
    # the `eyJ` anchor avoids matching arbitrary `ops_<identifier>` strings.
    ("1Password Service Account token", re.compile(r"ops_eyJ[A-Za-z0-9_\-]{30,}")),
    # Generic `api_key = "..."` / `secret: '...'` / `password=...` shapes.
    # Requires a >= 8-char quoted value so trivial placeholders ("") and
    # short config keys don't trip it.
    ("generic api_key/secret assignment",
     re.compile(
         r"""(?ix)
         \b(?:api[_-]?key|secret|password|passwd|token|access[_-]?key)\b
         \s*[:=]\s*
         ['"][^'"]{8,}['"]
         """,
     )),
]

# Inline allowlist marker. A `# SECRET_OK: <reason>` (>= 30 chars of reason)
# on the SAME added line exempts that line. Works with `#`, `//`, `--`, etc.
# because we only look for the literal `SECRET_OK:` token and the reason
# that follows it.
_SECRET_OK_RE = re.compile(r"SECRET_OK:\s*(.+)$")
_SECRET_OK_MIN_REASON = 30


def _truncate(s: str, limit: int = 80) -> str:
    s = s.rstrip()
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


def staged_diff() -> str:
    """Return the staged unified diff (`git diff --cached`)."""
    r = subprocess.run(
        ["git", "diff", "--cached", "--no-color", "--unified=0"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout if r.returncode == 0 else ""


def line_is_allowlisted(line: str) -> bool:
    """True iff the line carries an inline `# SECRET_OK: <reason>` with a
    substantive (>= 30 char) reason."""
    m = _SECRET_OK_RE.search(line)
    if not m:
        return False
    return len(m.group(1).strip()) >= _SECRET_OK_MIN_REASON


def scan_staged() -> list[tuple[str, int, str, str]]:
    """Parse the staged diff and return (file, line_no, pattern_desc,
    truncated_line) for every ADDED line matching a secret pattern that is
    NOT inline-allowlisted.

    Line numbers come from the hunk header (`@@ -a,b +c,d @@`): we track the
    new-file line counter and report the position of the offending `+` line."""
    hits: list[tuple[str, int, str, str]] = []
    cur_file: str | None = None
    new_lineno = 0
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

    for raw in staged_diff().splitlines():
        if raw.startswith("+++ b/"):
            cur_file = raw[len("+++ b/"):]
            continue
        if raw.startswith("--- "):
            continue
        if raw.startswith("@@"):
            m = hunk_re.match(raw)
            new_lineno = int(m.group(1)) if m else 0
            continue
        if raw.startswith("+"):
            content = raw[1:]
            if cur_file is not None and not line_is_allowlisted(content):
                for desc, rx in PATTERNS:
                    if rx.search(content):
                        hits.append((cur_file, new_lineno, desc, _truncate(content)))
                        break  # one finding per line is enough
            new_lineno += 1
        elif raw.startswith("-"):
            # Removed line — does not advance the new-file counter.
            continue
        else:
            # Context line (only present with non-zero -U; we use -U0, but
            # be robust). Advances the new-file counter.
            new_lineno += 1

    return hits


def main() -> int:
    hits = scan_staged()
    if not hits:
        print("[check_secrets] OK — no secret-shaped strings in the staged diff.")
        return 0
    print(
        f"[check_secrets] BLOCK — {len(hits)} secret-shaped string(s) in the "
        f"staged diff:",
        file=sys.stderr,
    )
    for file, lineno, desc, match in hits:
        print(f"  - {file}:{lineno}: {desc}", file=sys.stderr)
        print(f"      line: {match}", file=sys.stderr)
    print(
        "\nRoot-cause fix: remove the literal from source and replace with a "
        "runtime fetch (env var / secrets manager), then ROTATE the leaked "
        "credential — committing it leaves it in git history forever.\n"
        "If the match is a genuine public value or an unavoidable false "
        "positive, append an inline `# SECRET_OK: <reason>` comment "
        "(reason >= 30 chars) to that exact line. Do NOT --no-verify.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
