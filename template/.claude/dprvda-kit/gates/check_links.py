#!/usr/bin/env python3
# REASON: doc cross-reference gate — validates every markdown link (anchor + target file) resolves instead of relying on an external site-build step; native md parser replaces a prior subprocess invocation so the gate runs in ~2-3s on every commit, not 25s.
"""
scripts/check_links.py — doc cross-reference linker gate.

Walks every authored `.md` under `docs/` + sibling `.md`s in the
repo, extracts links + anchors, validates each link against the
filesystem and target-file anchor set.

What we check:

  - Missing target files: `[text](relative/path.md)` where the path
    doesn't resolve.
  - Missing anchors: `[text](page.md#anchor)` or `[text](#anchor)`
    where the anchor isn't a heading in the target page.

What we DON'T check (handled by other tooling / out of scope):

  - External links (`http://`, `https://`, `mailto:`).
  - Image links (`.png`, `.jpg`, etc. -- different validity rules).
  - Mermaid graph node references (parsed by Mermaid, not markdown).

Slugification:
  Python-markdown's default `toc.slugify` (lowercase, strip
  non-word/non-space, collapse spaces+separator, separator "-").
  If the project uses a different slug strategy, update SLUGIFY below.

Usage:
    python scripts/check_links.py
    python scripts/check_links.py --json

Exit codes:
    0 -- no broken links
    1 -- broken links found
    2 -- internal error

Sibling .md: scripts/check_links.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_ROOT = REPO_ROOT / "docs"

# Source files where broken links are tolerated (auto-generated /
# auto-mirrored / archived content).
LINK_EXEMPT_FILES: set[str] = set()

# Skip these path prefixes (relative to docs/).
EXEMPT_DIR_PREFIXES = (
    "archive/",   # archived content -- links allowed to rot
)

# `[text](url)` -- group "url" includes optional `#anchor` and ?query.
# Negative lookbehind to skip image links (`![alt](url)`).
LINK_RE = re.compile(r"(?<!\!)\[([^\]]+?)\]\(([^)]+?)\)")

# Reference-style: `[text]: url`.
REF_LINK_RE = re.compile(r"^\s*\[([^\]]+?)\]:\s*(\S+)\s*$", re.MULTILINE)

# ATX heading: `# Title`, `## Sub`, etc. Capture both the level (count
# of #) and the text. Optional trailing `{#explicit-id}` for explicit
# anchors.
HEADING_RE = re.compile(
    r"^(?P<hashes>#{1,6})\s+(?P<text>.+?)(?:\s*\{(?P<attrs>[^}]+)\})?\s*$",
    re.MULTILINE,
)

# Explicit anchor inside a heading's {attrs}: `{#custom-id}` (or with
# other attrs like `{.class #id}`).
EXPLICIT_ANCHOR_RE = re.compile(r"#([A-Za-z][\w-]*)")

# Code-block fences (triple backtick or tilde). Headings inside code
# blocks must NOT be treated as anchors. Strip code blocks before
# parsing headings.
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)

# Inline code spans: `code` or ``code with `backtick` inside``. Strip
# these before link extraction so `[label](path.md)` written as
# documentation example doesn't fire as a real broken link.
INLINE_CODE_RE = re.compile(r"``[^`]+?``|`[^`\n]+?`")

# Frontmatter detector -- pages with `frozen_at:` are historical
# snapshots and should not be link-checked (their links are often
# verbatim from upstream and may resolve only on the upstream site).
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FROZEN_AT_RE = re.compile(r"^frozen_at\s*:", re.MULTILINE)


@dataclass
class BrokenLink:
    severity: str  # "error" | "warn"
    source: str
    link: str
    detail: str

    def render(self) -> str:
        prefix = "ERROR" if self.severity == "error" else "WARN "
        return f"  {prefix}  {self.source}\n         link: {self.link}\n         {self.detail}"


def slugify(text: str) -> str:
    """Python-markdown's default toc.slugify -- lowercase, strip
    non-word/non-space, collapse spaces+separator, separator "-"."""
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore")
    value = re.sub(r"[^\w\s-]", "", value.decode("ascii")).strip().lower()
    value = re.sub(r"[-\s]+", "-", value)
    return value


def skip_source(rel_posix: str) -> bool:
    """Return True if the source file should be exempt from gating."""
    norm = rel_posix.replace("\\", "/")
    if any(norm.startswith(p) for p in EXEMPT_DIR_PREFIXES):
        return True
    if norm in LINK_EXEMPT_FILES:
        return True
    return False


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks AND inline code spans so headings /
    links inside them aren't parsed as section anchors / real
    references. (Documentation often shows example link syntax in
    `[label](path.md)` form -- that's not a real link.)"""
    text = FENCE_RE.sub("", text)
    text = INLINE_CODE_RE.sub("", text)
    return text


def is_frozen(md_path: Path) -> bool:
    """Return True if the .md has `frozen_at:` in its frontmatter.
    Frozen pages are historical snapshots -- their links may point at
    upstream resources that don't exist locally; skip link-checking."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False
    return bool(FROZEN_AT_RE.search(m.group(1)))


def extract_anchors(md_path: Path) -> set[str]:
    """Return the set of anchor IDs available in a markdown file:
    auto-slugified ATX headings + explicit `{#id}` overrides."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    text = strip_code_blocks(text)
    anchors: set[str] = set()
    # SERIAL_OK_LOOP: per-heading scan in one .md file (typically <= 50
    # headings); single-pass regex iteration is the right primitive
    for m in HEADING_RE.finditer(text):
        heading_text = m.group("text").strip()
        attrs = m.group("attrs") or ""
        em = EXPLICIT_ANCHOR_RE.search(attrs)
        if em:
            anchors.add(em.group(1))
            # Add auto-slug alongside explicit ID to be safe.
            anchors.add(slugify(heading_text))
        else:
            anchors.add(slugify(heading_text))
    return anchors


def extract_links(md_path: Path) -> list[tuple[str, str]]:
    """Return list of (link_text, url) tuples for inline + reference
    links in a markdown file. URL may include `#anchor` and `?query`.
    Skips fenced code blocks."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    text = strip_code_blocks(text)
    out: list[tuple[str, str]] = []
    # SERIAL_OK_LOOP: per-link scan in one .md file (typically <= 200
    # links); regex iteration is sequential by parser
    for m in LINK_RE.finditer(text):
        out.append((m.group(1), m.group(2)))
    # SERIAL_OK_LOOP: reference-style link parse in one .md (<= ~30 in
    # practice); sequential by parser
    for m in REF_LINK_RE.finditer(text):
        out.append((m.group(1), m.group(2)))
    return out


def is_external(url: str) -> bool:
    """External / non-checkable URL schemes."""
    lower = url.lower()
    return (
        lower.startswith("http://")
        or lower.startswith("https://")
        or lower.startswith("mailto:")
        or lower.startswith("ftp://")
        or lower.startswith("ftps://")
        or lower.startswith("//")  # protocol-relative
        or lower.startswith("data:")
    )


def is_skippable_extension(path_part: str) -> bool:
    """Return True if the path's file extension is something we don't
    cross-check (images, downloads, etc.)."""
    lower = path_part.lower()
    skippable = (
        ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
        ".pdf", ".zip", ".tar", ".gz",
        ".css", ".js",
        ".woff", ".woff2", ".ttf",
    )
    return any(lower.endswith(ext) for ext in skippable)


def split_url(url: str) -> tuple[str, str]:
    """Split a URL into (path, anchor). Strips ?query if present."""
    # Drop ?query first
    if "?" in url:
        url = url.split("?", 1)[0]
    if "#" in url:
        path, anchor = url.split("#", 1)
        return (path, anchor)
    return (url, "")


def resolve_target(source: Path, link_path: str) -> Path | None:
    """Resolve a relative link path against the source file's
    directory. Returns the resolved Path or None if the link is
    something we don't validate (empty, absolute outside docs/, etc.).
    """
    if not link_path:
        return None  # anchor-only link -- caller handles same-file case
    # Strip trailing slash for directory-style URLs (use_directory_urls).
    p = link_path.rstrip("/")
    if p.startswith("/"):
        # Absolute URL -- resolve from docs/ root.
        return DOCS_ROOT / p.lstrip("/")
    target = (source.parent / p).resolve()
    return target


def find_target_md(target: Path) -> Path | None:
    """Try to locate the .md file for a link target.

    `[text](other)` resolves to `other/index.md` OR `other.md`
    depending on layout. Filesystem-level: try .md first, then
    /index.md, then exact (might be a dir).
    """
    if target.suffix == ".md" and target.exists() and target.is_file():
        return target
    md_candidate = target.with_suffix(".md")
    if md_candidate.exists() and md_candidate.is_file():
        return md_candidate
    if target.is_dir():
        idx = target / "index.md"
        if idx.exists() and idx.is_file():
            return idx
        readme = target / "README.md"
        if readme.exists() and readme.is_file():
            return readme
    if target.exists() and target.is_file():
        return target
    return None


def collect_md_files() -> list[Path]:
    """Return every .md file under DOCS_ROOT, plus repo-level .mds
    we want to include in the link graph (top-level READMEs)."""
    files: list[Path] = []
    if DOCS_ROOT.exists():
        files.extend(DOCS_ROOT.rglob("*.md"))
    # Top-level repo .mds (CLAUDE.md, README*.md, AGENTS.md, etc.) so
    # cross-links from docs/ to repo-level files validate.
    # SERIAL_OK_LOOP: glob for <= 20 top-level .md files; sequential is fine
    for top in REPO_ROOT.glob("*.md"):
        files.append(top)
    return files


def check_link(
    source: Path,
    link_url: str,
    anchor_index: dict[Path, set[str]],
) -> str | None:
    """Validate one link. Returns None if valid, else an error detail
    string."""
    if is_external(link_url):
        return None
    path_part, anchor = split_url(link_url)
    if path_part == "":
        # Same-file anchor like `[text](#section)`.
        if not anchor:
            return None  # empty link, ignore
        if source not in anchor_index:
            anchor_index[source] = extract_anchors(source)
        if anchor not in anchor_index[source]:
            return f"missing anchor '#{anchor}' in same file"
        return None
    if is_skippable_extension(path_part):
        # Image / asset / etc. -- only check the file exists.
        target = resolve_target(source, path_part)
        if target is None:
            return None
        if not target.exists():
            return f"missing target file '{path_part}'"
        return None
    target = resolve_target(source, path_part)
    if target is None:
        return None
    md_target = find_target_md(target)
    if md_target is None:
        # Could be a non-md asset that exists raw.
        if target.exists():
            return None
        return f"missing target file '{path_part}'"
    if anchor:
        if md_target not in anchor_index:
            anchor_index[md_target] = extract_anchors(md_target)
        if anchor not in anchor_index[md_target]:
            try:
                rel_target = md_target.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                rel_target = str(md_target)
            return f"missing anchor '#{anchor}' in {rel_target}"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify every cross-reference link in docs/ resolves.",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    md_files = collect_md_files()
    anchor_index: dict[Path, set[str]] = {}
    broken: list[BrokenLink] = []

    # SERIAL_OK_LOOP: per-file link extraction; bounded by N_md; per-file
    # regex parse is microsecond-class so the for-loop is fine without
    # multiprocessing for typical repo sizes
    for md in md_files:
        try:
            rel = md.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            continue
        # Skip docs/ exempt prefixes.
        if rel.startswith("docs/"):
            rel_in_docs = rel[len("docs/"):]
            if skip_source(rel_in_docs):
                continue
        # Frozen pages: skip link-checking. Their content is intentionally
        # historical (snapshots, upstream-mirrored doc fragments), and
        # the links may point at external resources or earlier-state paths.
        if is_frozen(md):
            continue
        links = extract_links(md)
        # SERIAL_OK_LOOP: per-link-in-file validation; bounded by links-in-file
        for _text, url in links:
            err = check_link(md, url, anchor_index)
            if err is None:
                continue
            broken.append(
                BrokenLink(
                    severity="error",
                    source=rel,
                    link=url,
                    detail=err,
                )
            )

    if args.json:
        # SERIAL_OK_STDOUT: machine-readable summary; one stdout line for callers
        print(
            json.dumps(
                {
                    "ok": not broken,
                    "errors": [
                        {
                            "severity": b.severity,
                            "source": b.source,
                            "link": b.link,
                            "detail": b.detail,
                        }
                        for b in broken
                    ],
                },
                indent=2,
            )
        )
        return 0 if not broken else 1

    if not broken:
        print("[check_links] OK - 0 broken cross-references in authored docs.")
        return 0

    print(
        f"[check_links] {len(broken)} broken link(s) in authored docs:",
        file=sys.stderr,
    )
    # SERIAL_OK_LOOP: prints broken-link list to stderr; bounded by len(broken)
    for b in broken:
        # SERIAL_OK_STDOUT: ephemeral CLI gate stderr report; one line per broken link
        print(b.render(), file=sys.stderr)
    print(
        "\n  -> Fix: either add the missing anchor/file in the target page, "
        "or update the link in the source page to point at an existing target.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
