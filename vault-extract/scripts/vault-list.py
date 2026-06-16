#!/usr/bin/env python3
"""List all vaults in the federation with their overview.md frontmatter.

Usage: vault-list.py [--root <path>]

Walks <root>/*-vault/overview.md, parses the YAML frontmatter, and renders
one markdown section per vault for Claude to use during vault selection.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: pyyaml not found. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


EXCLUDED_DIRS = {".obsidian", ".git", ".trash", ".DS_Store"}


def split_frontmatter(text: str) -> str | None:
    """Return the YAML block between leading --- delimiters, or None."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    return parts[1]


def count_files(vault_dir: Path) -> int:
    """Count markdown content files (excluding meta files and dotdirs)."""
    excluded_names = {"overview.md", "CLAUDE.md"}
    count = 0
    for p in vault_dir.rglob("*.md"):
        if p.name in excluded_names:
            continue
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        count += 1
    return count


def render_vault(vault_dir: Path) -> str:
    """Render one vault as a markdown section."""
    overview_path = vault_dir / "overview.md"
    lines = [f"## {vault_dir.name}", "", f"- **Path**: `{vault_dir}`"]

    if not overview_path.exists():
        lines.append("- *(no overview.md — vault not fully scaffolded)*")
        lines.append("")
        return "\n".join(lines)

    text = overview_path.read_text(encoding="utf-8")
    fm_text = split_frontmatter(text)
    if fm_text is None:
        lines.append("- *(overview.md has no frontmatter)*")
        lines.append("")
        return "\n".join(lines)

    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        lines.append(f"- *(overview.md has malformed YAML: {e})*")
        lines.append("")
        return "\n".join(lines)

    if not isinstance(fm, dict):
        lines.append("- *(overview.md frontmatter is not a mapping)*")
        lines.append("")
        return "\n".join(lines)

    purpose = (fm.get("purpose") or "").strip()
    topics = fm.get("topics") or []
    domain = fm.get("domain", "")
    audience = fm.get("audience", "")
    status = fm.get("status", "")
    language = fm.get("language", "")
    source_kinds = fm.get("source_kinds") or []

    if purpose:
        lines.append(f"- **Purpose**: {purpose}")
    if topics:
        lines.append(f"- **Topics**: {', '.join(str(t) for t in topics)}")
    if domain:
        lines.append(f"- **Domain**: {domain}")
    if audience:
        lines.append(f"- **Audience**: {audience}")
    if status:
        lines.append(f"- **Status**: {status}")
    if language:
        lines.append(f"- **Language**: {language}")
    if source_kinds:
        lines.append(f"- **Source kinds**: {', '.join(str(s) for s in source_kinds)}")

    file_count = count_files(vault_dir)
    lines.append(f"- **Files**: {file_count}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="List vaults in the federation.")
    parser.add_argument("--root", type=str, default=None,
                        help="Federation root path. Default: ~/knowledge-vaults/")
    args = parser.parse_args()

    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")
    if not root.exists():
        print(f"Error: federation root does not exist: {root}", file=sys.stderr)
        print(f"Hint: run /vault-x:init first.", file=sys.stderr)
        sys.exit(1)

    vault_dirs = sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )

    print(f"# Knowledge Vaults — {root}")
    print()

    if not vault_dirs:
        print("No vaults yet. Create one with `/vault-x:create <name>`.")
        return

    print(f"{len(vault_dirs)} vault(s).")
    print()

    for vault_dir in vault_dirs:
        print(render_vault(vault_dir))


if __name__ == "__main__":
    main()
