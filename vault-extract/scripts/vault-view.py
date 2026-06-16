#!/usr/bin/env python3
"""Show the dynamic map of a single vault — dir tree, file frontmatter, link graph, orphans.

Usage: vault-view.py <name> [--root <path>]

Walks the vault, parses YAML frontmatter on every .md file, builds the
hermetic [[wiki-link]] graph, and reports orphans (files with no incoming
references) and unresolved links.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml not found. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


EXCLUDED_DIRS = {".obsidian", ".git", ".trash", ".DS_Store"}
META_FILES = {"overview.md", "CLAUDE.md"}
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def normalize_name(raw: str) -> str:
    name = raw.strip()
    if name.endswith("-vault"):
        name = name[: -len("-vault")]
    return name


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Extract frontmatter dict and body. Returns ({}, text) if no/invalid frontmatter."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
        if not isinstance(fm, dict):
            return {}, text
    except yaml.YAMLError:
        return {}, text
    return fm, parts[2].lstrip()


def build_tree(root: Path, prefix: str = "") -> list[str]:
    """Recursive dir tree, excluding meta dirs and dotfiles."""
    lines = []
    entries = sorted(
        (
            e for e in root.iterdir()
            if e.name not in EXCLUDED_DIRS and not e.name.startswith(".")
        ),
        key=lambda p: (not p.is_dir(), p.name.lower()),
    )
    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        suffix = "/" if entry.is_dir() else ""
        lines.append(f"{prefix}{connector}{entry.name}{suffix}")
        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(build_tree(entry, prefix + extension))
    return lines


def walk_content_files(vault_dir: Path) -> list[Path]:
    """All .md files except meta files and anything under excluded dirs."""
    files = []
    for p in sorted(vault_dir.rglob("*.md")):
        if p.name in META_FILES:
            continue
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        files.append(p)
    return files


def extract_wiki_links(body: str) -> list[str]:
    """Extract target names from [[wiki-link]] patterns. Strips |alias and #heading."""
    return [m.group(1).strip() for m in WIKI_LINK_RE.finditer(body)]


def render_file_summary(rel_path: str, fm: dict) -> str:
    title = fm.get("title") or Path(rel_path).stem
    bits = [f"- `{rel_path}` — **{title}**"]
    meta_bits = []
    for key in ("date", "tags", "source", "author", "status"):
        if key in fm and fm[key]:
            val = fm[key]
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            meta_bits.append(f"{key}={val}")
    if meta_bits:
        bits.append(" · " + " · ".join(meta_bits))
    return "".join(bits)


def main() -> None:
    parser = argparse.ArgumentParser(description="Map a single vault.")
    parser.add_argument("name", help="Vault name (with or without -vault suffix)")
    parser.add_argument("--root", type=str, default=None,
                        help="Federation root path. Default: ~/knowledge-vaults/")
    args = parser.parse_args()

    name = normalize_name(args.name)
    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")
    vault_dir = root / f"{name}-vault"
    if not vault_dir.exists():
        print(f"Error: vault not found at {vault_dir}", file=sys.stderr)
        sys.exit(1)

    # Header from overview.md
    overview_path = vault_dir / "overview.md"
    overview_fm = {}
    if overview_path.exists():
        overview_fm, _ = split_frontmatter(overview_path.read_text(encoding="utf-8"))

    display_name = overview_fm.get("name") or name
    purpose = (overview_fm.get("purpose") or "").strip()

    print(f"# {display_name}")
    print()
    if purpose:
        print(f"**Purpose**: {purpose}")
        print()

    # Layout (always shown)
    print("## Layout")
    print()
    print("```")
    print(f"{vault_dir.name}/")
    for line in build_tree(vault_dir):
        print(line)
    print("```")
    print()

    # Content
    files = walk_content_files(vault_dir)
    if not files:
        print("## Status")
        print()
        print("No content yet.")
        return

    # Parse each file
    file_data: dict[str, tuple[dict, list[str]]] = {}
    no_frontmatter_files: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        fm, body = split_frontmatter(text)
        rel = str(f.relative_to(vault_dir))
        if not fm:
            no_frontmatter_files.append(rel)
            file_data[rel] = ({}, extract_wiki_links(text))
        else:
            file_data[rel] = (fm, extract_wiki_links(body))

    # Files with frontmatter
    with_fm = [rel for rel in sorted(file_data) if rel not in no_frontmatter_files]
    if with_fm:
        print("## Files")
        print()
        for rel in with_fm:
            fm, _ = file_data[rel]
            print(render_file_summary(rel, fm))
        print()

    if no_frontmatter_files:
        print("## Files without frontmatter")
        print()
        for rel in sorted(no_frontmatter_files):
            print(f"- `{rel}`")
        print()

    # Resolution maps
    title_to_path: dict[str, str] = {}
    stem_to_path: dict[str, str] = {}
    for rel, (fm, _) in file_data.items():
        title = fm.get("title")
        if isinstance(title, str) and title and title not in title_to_path:
            title_to_path[title] = rel
        stem = Path(rel).stem
        stem_to_path.setdefault(stem, rel)

    def resolve(target: str) -> str | None:
        return title_to_path.get(target) or stem_to_path.get(target)

    # Graph
    forward: dict[str, list[tuple[str, str]]] = {}
    incoming: defaultdict[str, set[str]] = defaultdict(set)
    unresolved_per_file: defaultdict[str, list[str]] = defaultdict(list)

    for rel, (_, links) in file_data.items():
        edges = []
        seen_targets: set[str] = set()
        seen_unresolved: set[str] = set()
        for target in links:
            resolved = resolve(target)
            if resolved:
                if target not in seen_targets:
                    edges.append((target, resolved))
                    seen_targets.add(target)
                incoming[resolved].add(rel)
            else:
                if target not in seen_unresolved:
                    unresolved_per_file[rel].append(target)
                    seen_unresolved.add(target)
        forward[rel] = edges

    if any(forward[r] for r in forward):
        print("## Link graph")
        print()
        for rel in sorted(forward):
            edges = forward[rel]
            if not edges:
                continue
            targets_repr = ", ".join(f"[[{t}]]" for t, _ in edges)
            print(f"- `{rel}` → {targets_repr}")
        print()

    # Orphans: files with zero incoming references
    orphans = [rel for rel in sorted(file_data) if rel not in incoming]
    if orphans:
        print("## Orphans")
        print()
        print("Files with no incoming wiki-links:")
        print()
        for rel in orphans:
            print(f"- `{rel}`")
        print()

    # Unresolved
    if unresolved_per_file:
        print("## Unresolved links")
        print()
        for rel in sorted(unresolved_per_file):
            for t in unresolved_per_file[rel]:
                print(f"- `{rel}` → `[[{t}]]` (target not found in this vault)")
        print()


if __name__ == "__main__":
    main()
