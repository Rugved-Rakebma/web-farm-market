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

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402


def _main(args) -> None:
    template_path = C.TEMPLATES_DIR / "federation-CLAUDE.md"

    root = C.federation_root(args)
    root.mkdir(parents=True, exist_ok=True)

    claude_md = root / C.CLAUDE_MD
    if claude_md.exists() and not args.force:
        print(f"Federation root already initialized at {root}")
        print(f"  {C.CLAUDE_MD} exists. Use --force to overwrite.")
        return

    if not template_path.exists():
        raise C.VaultError(f"template not found at {template_path}")

    claude_md.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"Initialized federation root at {root}")
    print(f"  Wrote {C.CLAUDE_MD}")
    print()
    print("Next: create a vault with `/vault-x:create <name>`.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize the knowledge-vaults federation root.")
    C.add_root_arg(parser)
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing CLAUDE.md if present.")
    C.run(parser, _main)
