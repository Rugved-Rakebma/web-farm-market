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

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402


WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def build_tree(root: Path, prefix: str = "") -> list[str]:
    """Recursive dir tree, excluding meta dirs and dotfiles."""
    lines = []
    entries = sorted(
        (
            e for e in root.iterdir()
            if e.name not in C.EXCLUDED_DIRS and not e.name.startswith(".")
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


def _main(args) -> None:
    root = C.federation_root(args)
    C.require_root(root)
    ref = C.resolve(root, args.name)
    if ref is None:
        raise C.VaultError(f"vault not found: {args.name} (under {root})",
                           hint="Run /vault-x:list to see what exists.",
                           code=C.E_NOTFOUND)
    name = ref.rel      # never relative_to() — cannot raise
    vault_dir = ref.path

    # Header from overview.md
    overview_path = vault_dir / C.OVERVIEW
    overview_fm: dict = {}
    if overview_path.exists():
        overview_fm = C.parse_frontmatter(
            overview_path.read_text(encoding="utf-8")
        ).data

    display_name = overview_fm.get("name") or name
    purpose = (overview_fm.get("purpose") or "").strip()

    print(f"# {display_name}")
    print()
    if ref.tier == C.TIER2:
        print(f"**Tier {ref.tier}** · classifier `{ref.classifier}/`")
    else:
        print(f"**Tier {ref.tier}**")
    print()
    if purpose:
        print(f"**Purpose**: {purpose}")
        print()

    # Layout (always shown)
    print("## Layout")
    print()
    print("```")
    print(f"{ref.rel}/")
    for line in build_tree(vault_dir):
        print(line)
    print("```")
    print()

    # Content
    files = C.content_files(vault_dir)
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
        fm = C.parse_frontmatter(text)
        rel = str(f.relative_to(vault_dir))
        if not fm.data:
            no_frontmatter_files.append(rel)
            file_data[rel] = ({}, extract_wiki_links(text))
        else:
            file_data[rel] = (fm.data, extract_wiki_links(fm.body))

    # Files with frontmatter
    with_fm = [rel for rel in sorted(file_data) if rel not in no_frontmatter_files]
    if with_fm:
        print("## Files")
        print()
        for rel in with_fm:
            fm_data, _ = file_data[rel]
            print(render_file_summary(rel, fm_data))
        print()

    if no_frontmatter_files:
        print("## Files without frontmatter")
        print()
        for rel in sorted(no_frontmatter_files):
            print(f"- `{rel}`")
        print()

    # Resolution maps. stem_to_paths keeps ALL paths per stem so link resolution
    # can prefer a same-folder target (Obsidian's shortest-path behavior) — this
    # is what keeps each dated run's [[sources]] pointing within its own run folder
    # when a topic vault accumulates many runs with repeated stems.
    title_to_path: dict[str, str] = {}
    stem_to_paths: dict[str, list[str]] = defaultdict(list)
    for rel, (fm_data, _) in file_data.items():
        title = fm_data.get("title")
        if isinstance(title, str) and title and title not in title_to_path:
            title_to_path[title] = rel
        stem_to_paths[Path(rel).stem].append(rel)

    def resolve(target: str, source_rel: str) -> str | None:
        source_dir = str(Path(source_rel).parent)
        # 1. same-directory stem match
        for cand in stem_to_paths.get(target, []):
            if str(Path(cand).parent) == source_dir:
                return cand
        # 2. title match
        if target in title_to_path:
            return title_to_path[target]
        # 3. any stem match
        cands = stem_to_paths.get(target, [])
        return cands[0] if cands else None

    # Graph
    forward: dict[str, list[tuple[str, str]]] = {}
    incoming: defaultdict[str, set[str]] = defaultdict(set)
    unresolved_per_file: defaultdict[str, list[str]] = defaultdict(list)

    for rel, (_, links) in file_data.items():
        edges = []
        seen_targets: set[str] = set()
        seen_unresolved: set[str] = set()
        for target in links:
            resolved = resolve(target, rel)
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
    parser = argparse.ArgumentParser(description="Map a single vault.")
    parser.add_argument(
        "name",
        help="Vault reference: a path (research/local-llms), a tier-1 name "
             "(foo-vault), or a unique slug",
    )
    C.add_root_arg(parser)
    C.run(parser, _main)
