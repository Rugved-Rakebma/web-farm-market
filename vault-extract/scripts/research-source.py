#!/usr/bin/env python3
"""Write one vault-level raw source note into <vault>/sources/.

Usage:
  research-source.py --vault <ref> --url "<url>" --input <markdown-file>
      [--published <ISO date>] [--cited-by <n>] [--root <path>]

`--vault` takes any vault reference — `research/local-llms`, `personal-tax-vault`,
or a bare slug. The vault must already exist: this script never creates one.

The note is named from the URL (host + path), so re-running the same URL refreshes
it in place rather than accumulating duplicates, and two pages on the same host do
not collide. Used by /vault-x:grow's depth phase.
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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Write a vault-level raw source note.")
    ap.add_argument("--vault", dest="vault", default=None,
                    help="Vault reference: <classifier>/<slug>, <name>-vault, or a bare slug.")
    # Deprecated tier-2 shorthand — kept one release for in-flight grow transcripts.
    ap.add_argument("--vault-slug", dest="vault_slug_legacy", default=None,
                    help=argparse.SUPPRESS)
    ap.add_argument("--url", required=True, help="Original source URL.")
    ap.add_argument("--input", required=True,
                    help="File containing the source's full markdown (from web-x).")
    ap.add_argument("--published", default="unknown",
                    help="Source publish date if known (ISO). Default: unknown.")
    ap.add_argument("--cited-by", dest="cited_by", type=int, default=1,
                    help="How many runs in the vault cite this source.")
    C.add_root_arg(ap)
    return ap


def _main(args) -> None:
    ref_raw = args.vault
    if args.vault_slug_legacy:
        if ref_raw:
            raise C.VaultError("--vault and --vault-slug are mutually exclusive.",
                               hint="Use --vault; --vault-slug is deprecated.")
        ref_raw = args.vault_slug_legacy
        print("Warning: --vault-slug is deprecated; use --vault <ref> (accepts "
              "<classifier>/<slug>, <name>-vault, or a bare slug).", file=sys.stderr)
    if not ref_raw:
        raise C.VaultError("--vault is required.",
                           hint="e.g. --vault research/local-llms")

    try:
        markdown = Path(args.input).read_text(encoding="utf-8")
    except OSError as e:
        raise C.VaultError(f"cannot read markdown at {args.input}: {e}") from e

    root = C.federation_root(args)
    C.require_root(root)

    # create=False: fail closed. The path now comes from federation-wide
    # resolution rather than being recomputed here, so a slug that differs from
    # the one on disk can no longer produce a phantom miss.
    target = C.resolve_write_target(root, ref_raw, create=False)
    ref = target.ref

    sources_dir = ref.path / "sources"
    sources_dir.mkdir(exist_ok=True)

    path = sources_dir / f"{C.source_slug(args.url)}.md"
    today = datetime.date.today().isoformat()
    fm = C.dump_frontmatter({
        "title": C.host_of(args.url),
        "type": "raw-source",
        "source": args.url,
        "published": args.published or "unknown",
        "retrieved": today,
        "cited_by": args.cited_by,
        "tags": [],
    })
    path.write_text(fm + "\n" + markdown.strip() + "\n", encoding="utf-8")

    if not C.bump_updated(ref.path, today):
        print(f"Warning: no frontmatter in {ref.rel}/overview.md — "
              f"'updated:' not stamped.", file=sys.stderr)

    print(f"Wrote {ref.rel}/sources/{path.name}  "
          f"(published={args.published or 'unknown'}, cited_by={args.cited_by})")


if __name__ == "__main__":
    C.run(build_parser(), _main)
