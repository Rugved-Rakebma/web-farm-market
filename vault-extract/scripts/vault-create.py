#!/usr/bin/env python3
"""Create a new vault inside the federation.

Usage: vault-create.py <name> [--purpose "..."] [--root <path>]

Scaffolds <name>-vault/ with overview.md, CLAUDE.md, and .obsidian/.
Does NOT pre-impose source/ or any other subdirs.
Does NOT register the vault with Obsidian's obsidian.json.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
import textwrap
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"


def normalize_name(raw: str) -> str:
    """Strip -vault suffix, validate, return clean slug."""
    name = raw.strip()
    if name.endswith("-vault"):
        name = name[: -len("-vault")]
    if not name:
        print("Error: vault name cannot be empty.", file=sys.stderr)
        sys.exit(1)
    if re.search(r"[\s/\\]", name):
        print(f"Error: vault name must not contain whitespace or path separators: {raw!r}", file=sys.stderr)
        sys.exit(1)
    return name


def write_overview(vault_dir: Path, name: str, purpose: str) -> None:
    template = (TEMPLATES_DIR / "vault-overview.md").read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()

    content = template.replace("<vault-name>", name)
    content = content.replace("<YYYY-MM-DD>", today)

    # Replace the placeholder description line with the user's purpose.
    # Template has `  <description>` (2-space indent under `purpose: |`);
    # multi-line purposes are indented to match.
    indented_purpose = textwrap.indent(purpose.strip(), "  ")
    content = content.replace("  <description>", indented_purpose)

    (vault_dir / "overview.md").write_text(content, encoding="utf-8")


def write_claude_md(vault_dir: Path, name: str) -> None:
    template = (TEMPLATES_DIR / "vault-CLAUDE.md").read_text(encoding="utf-8")
    content = template.replace("<vault-name>", name)
    (vault_dir / "CLAUDE.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a new vault in the federation.")
    parser.add_argument("name", help="Vault name (with or without -vault suffix)")
    parser.add_argument("--purpose", default="TODO: describe this vault's purpose.",
                        help="One-line or paragraph purpose. Editable later in overview.md.")
    parser.add_argument("--root", type=str, default=None,
                        help="Federation root path. Default: ~/knowledge-vaults/")
    args = parser.parse_args()

    name = normalize_name(args.name)
    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")
    root.mkdir(parents=True, exist_ok=True)

    vault_dir = root / f"{name}-vault"
    if vault_dir.exists():
        print(f"Error: vault already exists at {vault_dir}", file=sys.stderr)
        sys.exit(1)

    vault_dir.mkdir()
    (vault_dir / ".obsidian").mkdir()
    write_overview(vault_dir, name, args.purpose)
    write_claude_md(vault_dir, name)

    print(f"Created vault at {vault_dir}")
    print(f"  - overview.md   (machine-readable identity)")
    print(f"  - CLAUDE.md     (write conventions for Claude)")
    print(f"  - .obsidian/    (empty; Obsidian will populate on first open)")
    print()
    print(f"Next steps:")
    print(f"  1. Open {vault_dir} once in Obsidian ('Open folder as vault').")
    print(f"  2. Edit overview.md to fill in topics, domain, etc.")
    print(f"  3. Edit CLAUDE.md to declare this vault's frontmatter schema.")


if __name__ == "__main__":
    main()
