#!/usr/bin/env python3
"""Materialize a deep-research run into a vault as a dated run folder.

Usage:
  research-scaffold.py --input <run.json> --vault <ref> --title "<short label>"
      [--classifier <name>] [--vault-title "<Topic>"] [--vault-purpose "<one line>"]
      [--root <path>] [--enriched <map.json>] [--allow-new-classifier]

`--vault` takes any vault reference:
  research/local-llms   an explicit tier-2 vault
  personal-tax-vault    a tier-1 vault (graduated, hand-maintained)
  local-llms            a bare slug, resolved federation-wide

Writes a self-contained run folder inside the resolved vault:

  YYYY-MM-DD-<title-slug>/
    report.md          synthesized findings + frontmatter
    blueprint.md       search angles (labels reconstructed from sources[].angle)
    sources.md         source ledger (quality, claim count, enrichment status)
    raw/<source>.md    web-x deep-reads, one per --enriched entry

A TIER-2 vault is scaffolded on first use from templates/. A tier-1 vault is never
machine-created: it is reached by /vault-x:create or by graduating a tier-2 vault.
Writing is fully deterministic — no LLM involved in this step.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402

CONF_RANK = {"high": 0, "medium": 1, "low": 2}

DEFAULT_PURPOSE = "TODO: describe this research topic."


# ─────────────────────────── helpers ───────────────────────────

def highest_confidence(findings: list) -> str:
    ranks = [CONF_RANK.get(f.get("confidence", "low"), 2) for f in findings]
    if not ranks:
        return "none"
    return {0: "high", 1: "medium", 2: "low"}[min(ranks)]


def run_folder_path(vault_dir: Path, today: str, slug: str) -> Path:
    base = f"{today}-{slug}"
    candidate = vault_dir / base
    n = 2
    while candidate.exists():
        candidate = vault_dir / f"{base}-{n}"
        n += 1
    return candidate


# ─────────────────────────── renderers ───────────────────────────

def render_report(data: dict, today: str, title: str) -> str:
    question = data.get("question", "").strip()
    findings = data.get("findings", []) or []
    sources = data.get("sources", []) or []

    fm = C.dump_frontmatter({
        "title": title or "Untitled research",
        "type": "research-report",
        "date": today,
        "confidence": highest_confidence(findings),
        "question": question,
        "sources": len(sources),
        "confirmed": len(findings),
        "tags": [],
    })

    blocks: list = []
    if question:
        blocks.append(f"# {question}")

    summary = (data.get("summary") or "").strip()
    blocks.append("## Summary\n\n" + (summary or "_No summary returned._"))

    fblock = ["## Findings", ""]
    if findings:
        for f in findings:
            claim = (f.get("claim") or "").strip()
            conf = f.get("confidence", "unknown")
            srcs = f.get("sources", []) or []
            evidence = (f.get("evidence") or "").strip()
            fblock.append(f"### {claim}")
            fblock.append(f"- **Confidence:** {conf}")
            if srcs:
                fblock.append("- **Sources:** " + " · ".join(srcs))
            if evidence:
                fblock.append(f"- **Evidence:** {evidence}")
            fblock.append("")
    else:
        fblock.append("_No claims survived adversarial verification._")
    blocks.append("\n".join(fblock).rstrip())

    caveats = (data.get("caveats") or "").strip()
    if caveats:
        blocks.append("## Caveats\n\n" + caveats)

    open_qs = data.get("openQuestions", []) or []
    if open_qs:
        blocks.append("\n".join(["## Open questions", ""] + [f"- {q}" for q in open_qs]))

    blocks.append("---\n\nSee [[sources]] · [[blueprint]]")
    return fm + "\n" + "\n\n".join(blocks) + "\n"


def render_blueprint(data: dict, today: str, title: str) -> str:
    question = data.get("question", "").strip()
    sources = data.get("sources", []) or []
    stats = data.get("stats", {}) or {}

    # Angle labels survive per-source; queries/rationale do not return.
    angles = []
    for s in sources:
        a = s.get("angle")
        if a and a not in angles:
            angles.append(a)

    fm = C.dump_frontmatter({
        "title": f"Blueprint — {title}" if title else "Blueprint",
        "type": "research-blueprint",
        "date": today,
        "tags": [],
    })

    parts = [fm, "# Blueprint\n", "## Question\n", question or "_(none)_", ""]
    parts.append("## Search angles\n")
    if angles:
        parts.extend(f"- {a}" for a in angles)
    else:
        parts.append("_No angles recorded._")
    parts.append("")
    parts.append(
        "> Angle labels are reconstructed from each source's originating angle. "
        "The exact search queries are not returned by the deep-research harness.\n"
    )
    if stats:
        parts.append("## Run stats\n")
        parts.append("```json")
        parts.append(json.dumps(stats, indent=2))
        parts.append("```")
    return "\n".join(parts).rstrip() + "\n"


def render_sources(data: dict, today: str, enriched: dict, title: str) -> str:
    question = data.get("question", "").strip()  # noqa: F841 — kept for parity
    sources = data.get("sources", []) or []

    fm = C.dump_frontmatter({
        "title": f"Sources — {title}" if title else "Sources",
        "type": "source-ledger",
        "date": today,
        "count": len(sources),
        "tags": [],
    })

    parts = [fm, "# Sources\n"]
    if not sources:
        parts.append("_No sources fetched._")
        return "\n".join(parts).rstrip() + "\n"

    parts.append("| Source | Quality | Claims | Angle | Raw |")
    parts.append("|--------|---------|--------|-------|-----|")
    for s in sources:
        url = s.get("url", "")
        quality = s.get("quality", "?")
        claims = s.get("claimCount", 0)
        angle = s.get("angle", "")
        # web-x deep-read only for sources the native fetch skimmed. The link stem
        # must match the raw filename below — both use source_slug (host + path),
        # so two pages on one host no longer collapse onto one note.
        raw = f"[[{C.source_slug(url)}]]" if url in enriched else "—"
        parts.append(f"| {url} | {quality} | {claims} | {angle} | {raw} |")
    return "\n".join(parts).rstrip() + "\n"


def render_raw(url: str, markdown: str, today: str) -> str:
    fm = C.dump_frontmatter({
        "title": C.host_of(url),
        "type": "raw-source",
        "source": url,
        "date": today,
        "tags": [],
    })
    return fm + "\n" + (markdown or "").strip() + "\n"


# ─────────────────────────── main ───────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scaffold a deep-research run into a vault (either tier).")
    p.add_argument("--input", required=True, help="Path to the deep-research run JSON.")
    p.add_argument("--vault", dest="vault", default=None,
                   help="Vault reference: <classifier>/<slug>, <name>-vault, or a bare slug.")
    # Deprecated tier-2 shorthand. Kept one release: shell history and in-flight
    # /vault-x:grow transcripts still emit it.
    p.add_argument("--vault-slug", dest="vault_slug_legacy", default=None,
                   help=argparse.SUPPRESS)
    p.add_argument("--classifier", default=C.DEFAULT_CLASSIFIER,
                   help=f"Classifier for a NEW tier-2 vault. Default: {C.DEFAULT_CLASSIFIER}")
    p.add_argument("--title", required=True,
                   help="Short human title for the run's report + run-folder slug.")
    p.add_argument("--vault-title", dest="vault_title", default=None,
                   help="Display title for a NEW tier-2 vault's overview. Default: derived from the slug.")
    p.add_argument("--vault-purpose", dest="vault_purpose", default=None,
                   help="One-line purpose for a NEW tier-2 vault's overview.")
    p.add_argument("--enriched", default=None,
                   help="Path to {url: raw_markdown} JSON from web-x.")
    p.add_argument("--allow-new-classifier", dest="allow_new_classifier",
                   action="store_true",
                   help="Permit creating a classifier directory that does not exist yet.")
    C.add_root_arg(p)
    return p


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

    title = args.title.strip()
    if not title:
        raise C.VaultError("--title cannot be empty.")

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise C.VaultError(f"cannot read run JSON at {args.input}: {e}") from e
    if not isinstance(data, dict):
        raise C.VaultError(f"run JSON at {args.input} is not an object.")

    enriched: dict = {}
    if args.enriched:
        try:
            enriched = json.loads(Path(args.enriched).read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError) as e:
            raise C.VaultError(
                f"cannot read enrichment JSON at {args.enriched}: {e}") from e

    today = datetime.date.today().isoformat()
    root = C.federation_root(args)
    C.require_root(root)

    target = C.resolve_write_target(
        root, ref_raw,
        default_classifier=args.classifier,
        create=True,
        allow_new_classifier=args.allow_new_classifier,
    )
    ref = target.ref

    if target.must_create:
        vault_title = (args.vault_title.strip() if args.vault_title
                       else ref.slug.replace("-", " ").title())
        written = C.scaffold_tier2_vault(
            ref,
            vault_title=vault_title,
            purpose=(args.vault_purpose or DEFAULT_PURPOSE),
            today=today,
        )
        if written:
            print(f"Scaffolded {ref.rel}/ ({', '.join(written)})")
    elif args.vault_title or args.vault_purpose:
        print(f"Note: --vault-title/--vault-purpose ignored; {ref.rel} already exists.",
              file=sys.stderr)

    # Stamp the staleness signal on the RESOLVED target, so a run into a tier-1
    # vault updates that vault rather than a tier-2 path that may not exist.
    if not C.bump_updated(ref.path, today):
        print(f"Warning: no frontmatter in {ref.rel}/overview.md — "
              f"'updated:' not stamped.", file=sys.stderr)

    run_dir = run_folder_path(ref.path, today, C.slugify(title, fallback="run"))
    run_dir.mkdir()

    (run_dir / "report.md").write_text(render_report(data, today, title), encoding="utf-8")
    (run_dir / "blueprint.md").write_text(render_blueprint(data, today, title), encoding="utf-8")
    (run_dir / "sources.md").write_text(
        render_sources(data, today, enriched, title), encoding="utf-8")

    raw_written = 0
    if enriched:
        raw_dir = run_dir / "raw"
        raw_dir.mkdir()
        for url, markdown in enriched.items():
            (raw_dir / f"{C.source_slug(url)}.md").write_text(
                render_raw(url, markdown, today), encoding="utf-8")
            raw_written += 1

    print(f"Wrote research run to {run_dir}")
    print(f"  - report.md      ({len(data.get('findings', []) or [])} findings)")
    print("  - blueprint.md")
    print(f"  - sources.md     ({len(data.get('sources', []) or [])} sources)")
    if raw_written:
        print(f"  - raw/           ({raw_written} web-x-enriched)")
    print()
    print(f"Target: {ref.label}")
    print(f"View it: /vault-x:view {ref.rel}")


if __name__ == "__main__":
    C.run(build_parser(), _main)
