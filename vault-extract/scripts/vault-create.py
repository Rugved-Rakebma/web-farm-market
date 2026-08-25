#!/usr/bin/env python3
"""Create a new TIER-1 vault inside the federation.

Usage: vault-create.py <name> [--purpose "..."] [--root <path>]

Scaffolds <name>-vault/ with overview.md, CLAUDE.md, and .obsidian/.
Tier 1 only — machine-produced tier-2 vaults (<classifier>/<slug>/) are created
by the research scaffolder, never here.

Does NOT pre-impose source/ or any other subdirs.
Does NOT register the vault with Obsidian's obsidian.json.
"""
from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402


def write_overview(vault_dir: Path, name: str, purpose: str) -> None:
    text = C.render_template(
        "vault-overview.md",
        {
            "<vault-name>": name,
            "<YYYY-MM-DD>": datetime.date.today().isoformat(),
            "  <description>": purpose,
        },
        indent_keys=("  <description>",),
    )
    (vault_dir / C.OVERVIEW).write_text(text, encoding="utf-8")


def write_claude_md(vault_dir: Path, name: str) -> None:
    text = C.render_template("vault-CLAUDE.md", {"<vault-name>": name})
    (vault_dir / C.CLAUDE_MD).write_text(text, encoding="utf-8")


def _main(args) -> None:
    name = C.strip_vault_suffix(args.name.strip())
    root = C.federation_root(args)
    root.mkdir(parents=True, exist_ok=True)

    # validate_slug (inside target_ref) rejects whitespace, path separators,
    # empty names, reserved names, and a residual -vault suffix.
    ref = C.target_ref(root, name, None)

    # Cross-tier guard: a topic must exist at exactly one tier. Without this,
    # creating 'foo' while research/foo/ exists forks the topic into two vaults.
    for other in C.discover(root).vaults:
        if other.slug == name and other.rel != ref.rel:
            raise C.VaultError(
                f"'{other.rel}' already holds the topic '{name}' at tier {other.tier}.",
                hint=(f"Graduating is a MOVE, not a create:\n"
                      f"  git -C {root} mv {other.rel} {ref.dirname}\n"
                      f"then rewrite {ref.dirname}/CLAUDE.md and update its overview.md "
                      f"(see the graduation test in {root}/CLAUDE.md)."),
                code=C.E_TIER)

    if ref.path.exists():
        raise C.VaultError(f"vault already exists at {ref.path}")

    vault_dir = ref.path
    vault_dir.mkdir()
    (vault_dir / ".obsidian").mkdir()
    write_overview(vault_dir, name, args.purpose)
    write_claude_md(vault_dir, name)

    print(f"Created vault at {vault_dir}")
    print(f"  - {C.OVERVIEW}   (machine-readable identity)")
    print(f"  - {C.CLAUDE_MD}     (write conventions for Claude)")
    print("  - .obsidian/    (empty; Obsidian will populate on first open)")
    print()
    print("This is a TIER-1 vault: hand-maintained, not reproducible by tooling.")
    print(f"The '{C.VAULT_SUFFIX}' suffix IS the tier-1 marker — tier-2 vaults live at")
    print(f"'<classifier>/<slug>/' and never carry it.")
    print()
    print("Next steps:")
    print(f"  1. Open {vault_dir} once in Obsidian ('Open folder as vault').")
    print(f"  2. Edit {C.OVERVIEW} to fill in topics, domain, etc.")
    print(f"  3. Edit {C.CLAUDE_MD} to declare this vault's frontmatter schema.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create a new tier-1 vault in the federation.")
    parser.add_argument(
        "name",
        help="Vault name (with or without the -vault suffix). Always creates "
             "tier 1 at <name>-vault/.")
    parser.add_argument("--purpose", default="TODO: describe this vault's purpose.",
                        help="One-line or paragraph purpose. Editable later in overview.md.")
    C.add_root_arg(parser)
    C.run(parser, _main)
