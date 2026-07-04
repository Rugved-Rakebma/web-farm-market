#!/usr/bin/env python3
"""Write one vault-level raw source note into research/<slug>/sources/.

Usage:
  research-source.py --vault-slug <slug> --url <url> --input <markdown-file>
      [--published <date>] [--cited-by <n>] [--root <path>]

Part of /vault-x:grow — the deliberate depth pass. Given a source's full text
(extracted by web-x) it writes a deduped evidence note under the topic vault's
shared sources/ library and bumps the vault's `updated` staleness stamp.

Deterministic — no LLM in the writing step. Re-running for the same URL
overwrites (refreshes) the note.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("Error: pyyaml not found. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


RESEARCH_NAMESPACE = "research"


def slugify(text: str, limit: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0]
    return s or "source"


def host_of(url: str) -> str:
    try:
        h = urlparse(url).hostname or "source"
    except ValueError:
        h = "source"
    return h.replace("www.", "").strip(".") or "source"


def source_slug(url: str) -> str:
    """Unique-per-URL slug from host + path (so two pages on the same host don't collide)."""
    try:
        p = urlparse(url)
        base = (p.hostname or "source").replace("www.", "") + (p.path or "")
    except ValueError:
        base = url
    return slugify(base)


def dump_frontmatter(fields: dict) -> str:
    body = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{body}---\n"


def bump_updated(vault_dir: Path, today: str) -> None:
    """Set overview.md's `updated:` to today (inserting after `created:` if absent)."""
    overview = vault_dir / "overview.md"
    if not overview.exists():
        return
    lines = overview.read_text(encoding="utf-8").splitlines(keepends=True)
    out, done = [], False
    for line in lines:
        if not done and re.match(r"^updated:\s", line):
            out.append(f"updated: {today}\n")
            done = True
        else:
            out.append(line)
    if not done:
        rebuilt = []
        for line in out:
            rebuilt.append(line)
            if not done and re.match(r"^created:\s", line):
                rebuilt.append(f"updated: {today}\n")
                done = True
        out = rebuilt
    overview.write_text("".join(out), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Write a vault-level raw source note.")
    ap.add_argument("--vault-slug", dest="vault_slug", required=True, help="Topic vault slug under research/.")
    ap.add_argument("--url", required=True, help="Original source URL.")
    ap.add_argument("--input", required=True, help="File containing the source's full markdown (from web-x).")
    ap.add_argument("--published", default="unknown", help="Source publish date if known (ISO). Default: unknown.")
    ap.add_argument("--cited-by", dest="cited_by", type=int, default=1, help="How many runs in the vault cite this source.")
    ap.add_argument("--root", default=None, help="Federation root. Default: ~/knowledge-vaults/")
    args = ap.parse_args()

    try:
        markdown = Path(args.input).read_text(encoding="utf-8")
    except OSError as e:
        print(f"Error: cannot read markdown at {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")
    vault_dir = root / RESEARCH_NAMESPACE / slugify(args.vault_slug)
    if not vault_dir.exists():
        print(f"Error: topic vault not found: {vault_dir} (run research into it first)", file=sys.stderr)
        sys.exit(1)

    sources_dir = vault_dir / "sources"
    sources_dir.mkdir(exist_ok=True)

    path = sources_dir / f"{source_slug(args.url)}.md"   # URL-derived → same URL refreshes in place
    today = datetime.date.today().isoformat()
    fm = dump_frontmatter({
        "title": host_of(args.url),
        "type": "raw-source",
        "source": args.url,
        "published": args.published or "unknown",
        "retrieved": today,
        "cited_by": args.cited_by,
        "tags": [],
    })
    path.write_text(fm + "\n" + markdown.strip() + "\n", encoding="utf-8")
    bump_updated(vault_dir, today)

    print(f"Wrote {path.relative_to(root)}  (published={args.published or 'unknown'}, cited_by={args.cited_by})")


if __name__ == "__main__":
    main()
