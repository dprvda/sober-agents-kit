#!/usr/bin/env python3
# REASON: Layer-4 build-hardening gate — exists because no other gate scans the COMPILED ELF/PE instead of source, so a literal secret baked into rodata bypasses every source-level linter the moment the literal moves to a non-monitored file. This gate scans the emitted binaries for hex private keys, GitHub PATs, sk- tokens, 1Password Service Account tokens, and AWS AKIA keys, replacing source-only review of secret-handling code. Forces re-detection if a refactor accidentally re-introduces a baked literal. No-op on doc-only commits where no fresh binary exists.
"""Pre-commit gate: scan compiled binaries for secret-shaped strings.

Runs every commit (`always_run: true`, `pass_filenames: false`). For each
known binary path that exists on disk, shells `strings -a <bin>` and
greps each line against the documented pattern set. Reports per-binary
hits + total count, exits 1 if any hit; exits 0 if the binaries are
clean OR if none exist.

CI / dev caveats:
- Fresh checkout with no `cargo build` run yet: no binary present, gate
  no-ops. Operator triggers `cargo build --release` before this gate is
  meaningful.
- `strings` is part of `binutils`; standard on Linux + WSL2 + MSYS2.
  Missing-tool path errors clearly + exits 1 (NOT silent allow).
- The gate is allowlist-free by design: the right fix on a real hit is
  "remove the literal from source", not an allowlist that drifts.
  Operator can still `--no-verify` in a true emergency (not recommended).

CONFIGURE: Edit BINARIES below to list the compiled output paths for
your project (relative to repo root). Use __PROJECT_NAME__ as a
placeholder when generating from a template installer — replace with
the actual binary name(s) before use.

Patterns:
  * `0x[0-9a-fA-F]{64}` — hex private key (full 32 bytes)
  * `ghp_[A-Za-z0-9]{36}` — GitHub Personal Access Token
  * `sk-[A-Za-z0-9]{32,}` — generic API token (sk- prefix)
  * `ops_[A-Za-z0-9_-]{60,}` — 1Password Service Account token
  * `AKIA[A-Z0-9]{16}` — AWS access key ID
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# Binaries to scan when present. Edit this list to name the compiled
# output paths for your project (relative to REPO_ROOT). Both
# release and debug/cross builds can be listed — missing paths are
# silently skipped.
# Example entries for a project named __PROJECT_NAME__:
BINARIES = [
    # Host-arch release builds (Windows .exe + Linux ELF)
    "target/release/__PROJECT_NAME__",
    "target/release/__PROJECT_NAME__.exe",
    # ARM cross-build outputs (canonical prod artifact)
    "target/aarch64-unknown-linux-gnu/release/__PROJECT_NAME__",
    "target/aarch64-unknown-linux-gnu/release-fast/__PROJECT_NAME__",
]

REPO_ROOT = Path(__file__).resolve().parents[3]

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("hex private key (64 hex chars)", re.compile(r"0x[0-9a-fA-F]{64}")),
    ("GitHub Personal Access Token", re.compile(r"ghp_[A-Za-z0-9]{36}")),
    ("sk- API token", re.compile(r"sk-[A-Za-z0-9]{32,}")),
    # Tightened to the JWT-style `eyJ` header so we don't match arbitrary
    # `ops_<identifier>` rodata blobs. Real 1Password SA tokens begin `ops_eyJ`.
    ("1Password Service Account token", re.compile(r"ops_eyJ[A-Za-z0-9_\-]{30,}")),
    ("AWS access key ID", re.compile(r"AKIA[A-Z0-9]{16}")),
]

# Allowlist of known-public 64-char hex values intentionally baked into
# the binary at compile time. Each entry needs an inline comment naming
# the source so a reviewer can verify the value is genuinely public.
# Adding a new entry is a deliberate per-value decision — NOT a bypass.
ALLOWED_HEX: dict[str, str] = {
    # Rust stdlib false-positive, NOT a secret. `strings` concatenates the
    # `"0x"` radix-prefix literal in library/core/src/fmt/num.rs with the
    # adjacent DEC_DIGITS_LUT; the regex then matches `0x` + the LUT's first
    # 64 chars. Toolchain-emitted into every Rust binary (no source literal
    # to remove — it's in the standard library).
    "0x0001020304050607080910111213141516171819202122232425262728293031":
        "Rust stdlib DEC_DIGITS_LUT + adjacent 0x radix prefix (core/fmt/num.rs)",
}


def _truncate(s: str, limit: int = 80) -> str:
    s = s.rstrip()
    if len(s) <= limit:
        return s
    return s[: limit - 3] + "..."


_PRINTABLE_ASCII = bytes(range(0x20, 0x7F)) + b"\t"
_PYTHON_STRINGS_MIN_LEN = 4  # match GNU `strings` default


def _python_strings(bin_path: Path) -> list[str]:
    """Pure-Python `strings -a` equivalent — Windows hosts have no
    binutils. Streams the file, emits each maximal run of printable
    ASCII bytes of length >= 4 (same default as GNU strings)."""
    out: list[str] = []
    buf = bytearray()
    table = bytearray(256)
    for b in _PRINTABLE_ASCII:
        table[b] = 1
    with bin_path.open("rb") as fh:
        while True:
            chunk = fh.read(1 << 16)
            if not chunk:
                break
            for b in chunk:
                if table[b]:
                    buf.append(b)
                elif len(buf) >= _PYTHON_STRINGS_MIN_LEN:
                    out.append(buf.decode("ascii", "replace"))
                    buf.clear()
                else:
                    buf.clear()
    if len(buf) >= _PYTHON_STRINGS_MIN_LEN:
        out.append(buf.decode("ascii", "replace"))
    return out


def _scan_one(bin_path: Path) -> list[tuple[str, str, str]]:
    """Return list of (bin, pattern_desc, truncated_match) tuples."""
    if not bin_path.exists():
        return []
    lines: list[str]
    if shutil.which("strings") is not None:
        try:
            out = subprocess.run(
                ["strings", "-a", str(bin_path)],
                capture_output=True,
                text=True,
                check=True,
                errors="replace",
            )
        except subprocess.CalledProcessError as e:
            print(
                f"[check_binary_secrets] ERROR: strings -a {bin_path} failed: "
                f"rc={e.returncode} stderr={e.stderr.strip()[:200]}",
                file=sys.stderr,
            )
            sys.exit(1)
        lines = out.stdout.splitlines()
    else:
        # Windows host etc. — pure-Python fallback so the gate stays
        # fail-closed without a binutils dependency.
        lines = _python_strings(bin_path)
    hits: list[tuple[str, str, str]] = []
    for line in lines:
        for desc, rx in PATTERNS:
            m = rx.search(line)
            if m is None:
                continue
            if m.group() in ALLOWED_HEX:
                continue
            hits.append((str(bin_path.relative_to(REPO_ROOT)), desc, _truncate(line)))
            # one finding per line is enough; move to next line
            break
    return hits


def main() -> int:
    targets = [REPO_ROOT / b for b in BINARIES]
    present = [p for p in targets if p.exists()]
    if not present:
        # Doc-only / fresh-checkout / pre-first-build commit. The gate
        # is meaningful only after `cargo build --release` — no-op cleanly.
        print(
            "[check_binary_secrets] OK — no compiled binaries found "
            "(target/release/... etc.). Pre-build or doc-only commit; nothing to scan."
        )
        return 0
    all_hits: list[tuple[str, str, str]] = []
    for p in present:
        all_hits.extend(_scan_one(p))
    if not all_hits:
        names = ", ".join(p.name for p in present)
        print(
            f"[check_binary_secrets] OK — {len(present)} binary(ies) scanned "
            f"({names}); zero secret-shaped strings found."
        )
        return 0
    print(
        f"[check_binary_secrets] BLOCK — {len(all_hits)} secret-shaped string(s) "
        f"in compiled binaries:",
        file=sys.stderr,
    )
    for bin_name, desc, match in all_hits:
        print(f"  - {bin_name}: {desc}", file=sys.stderr)
        print(f"      match: {match}", file=sys.stderr)
    print(
        "\nRoot-cause fix: find the source literal (grep the workspace for "
        "the leaked value or its prefix) and replace with a runtime fetch "
        "(env var, AWS SSM, 1Password). Do NOT --no-verify; the "
        "leaked secret stays in git history.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
