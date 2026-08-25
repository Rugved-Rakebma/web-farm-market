#!/usr/bin/env python3
"""List all vaults in the federation with their overview.md frontmatter.

Usage: vault-list.py [--root <path>]

Enumerates the two-tier federation — tier-1 `<name>-vault/` and tier-2
`<classifier>/<slug>/` — parses each vault's YAML frontmatter, and renders one
section per vault for Claude to use during selection. Placements that violate
the standard are reported under `## Anomalies` rather than silently ignored.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402


def render_vault(ref: C.VaultRef) -> str:
    """Render one vault as a markdown section."""
    overview_path = ref.path / C.OVERVIEW
    lines = [f"### {ref.rel}", "", f"- **Path**: `{ref.path}`"]

    if not overview_path.exists():
        lines.append("- *(no overview.md — vault not fully scaffolded)*")
        lines.append("")
        return "\n".join(lines)

    fm = C.load_frontmatter(overview_path)
    if fm.raw is None:
        lines.append("- *(overview.md has no frontmatter)*")
        lines.append("")
        return "\n".join(lines)

    if fm.error:
        if fm.error.startswith("malformed YAML"):
            lines.append(f"- *(overview.md has {fm.error})*")
        else:
            lines.append(f"- *(overview.md {fm.error})*")
        lines.append("")
        return "\n".join(lines)

    data = fm.data
    purpose = (data.get("purpose") or "").strip()
    topics = data.get("topics") or []
    domain = data.get("domain", "")
    audience = data.get("audience", "")
    status = data.get("status", "")
    language = data.get("language", "")
    source_kinds = data.get("source_kinds") or []
    created = data.get("created", "")
    updated = data.get("updated", "")

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
    if created or updated:
        lines.append(f"- **Created**: {created or '—'} · **Updated**: {updated or '—'}")

    lines.append(f"- **Files**: {len(C.content_files(ref.path))}")
    lines.append("")
    return "\n".join(lines)


def _main(args) -> None:
    root = C.federation_root(args)
    C.require_root(root)

    d = C.discover(root)

    print(f"# Knowledge Vaults — {root}")
    print()

    if not d.vaults and not d.anomalies:
        print("No vaults yet. Create one with `/vault-x:create <name>` or `/vault-x:research`.")
        return

    if d.vaults:
        n1 = sum(1 for v in d.vaults if v.tier == C.TIER1)
        n2 = len(d.vaults) - n1
        print(f"{len(d.vaults)} vault(s) — {n1} tier-1, {n2} tier-2.")
        print()

        # d.vaults is sorted by (tier, classifier, slug), so a change in either
        # component is exactly a group boundary — no regrouping pass needed.
        group = None
        for ref in d.vaults:
            key = (ref.tier, ref.classifier)
            if key != group:
                group = key
                if ref.tier == C.TIER1:
                    print("## Tier 1 — graduated")
                else:
                    print(f"## Tier 2 — {ref.classifier}/")
                print()
            print(render_vault(ref))
    else:
        print("No vaults yet. Create one with `/vault-x:create <name>` or `/vault-x:research`.")
        print()

    if d.anomalies:
        print("## Anomalies")
        print()
        print("These placements violate the two-tier standard, so they are not "
              "resolvable as vaults:")
        print()
        for a in d.anomalies:
            print(f"- `{a.rel}` — {a.reason}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List vaults in the federation.")
    C.add_root_arg(parser)
    C.run(parser, _main)
