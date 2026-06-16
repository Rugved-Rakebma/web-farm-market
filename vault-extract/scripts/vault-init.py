#!/usr/bin/env python3
"""Initialize the knowledge-vaults federation root.

Usage: vault-init.py [--root <path>] [--force]

Default federation root: ~/knowledge-vaults/. Override with --root.
Idempotent — won't overwrite an existing CLAUDE.md unless --force.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = PLUGIN_ROOT / "templates" / "federation-CLAUDE.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the knowledge-vaults federation root.")
    parser.add_argument("--root", type=str, default=None,
                        help="Federation root path. Default: ~/knowledge-vaults/")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing CLAUDE.md if present.")
    args = parser.parse_args()

    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")
    root.mkdir(parents=True, exist_ok=True)

    claude_md = root / "CLAUDE.md"
    if claude_md.exists() and not args.force:
        print(f"Federation root already initialized at {root}")
        print(f"  CLAUDE.md exists. Use --force to overwrite.")
        return

    if not TEMPLATE_PATH.exists():
        print(f"Error: template not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)

    claude_md.write_text(TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Initialized federation root at {root}")
    print(f"  Wrote CLAUDE.md")
    print()
    print(f"Next: create a vault with `/vault-x:create <name>`.")


if __name__ == "__main__":
    main()
