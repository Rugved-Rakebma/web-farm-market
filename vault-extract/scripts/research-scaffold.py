#!/usr/bin/env python3
"""Materialize a deep-research run into a research topic vault as a dated run folder.

Usage:
  research-scaffold.py --input <run.json> --vault-slug <slug> --title "<short label>"
      [--vault-title "<Topic>"] [--vault-purpose "<one line>"] [--root <path>] [--enriched <map.json>]

Reads the JSON returned by Workflow({name:"deep-research", ...}) and writes a
self-contained run folder under ~/knowledge-vaults/research/<vault-slug>/:

  YYYY-MM-DD-<title-slug>/
    report.md      synthesized findings + frontmatter
    blueprint.md   search angles (labels reconstructed from sources[].angle)
    sources.md     source ledger (quality, claim count, enrichment status)
    raw/<host>.md  web-x deep-reads, one per --enriched entry

The topic vault (research/<slug>/) is scaffolded on first use from templates/.
Writing is fully deterministic — no LLM involved in this step.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
import textwrap
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except ImportError:
    print("Error: pyyaml not found. Install: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
RESEARCH_NAMESPACE = "research"

CONF_RANK = {"high": 0, "medium": 1, "low": 2}


# ─────────────────────────── helpers ───────────────────────────

def slugify(text: str) -> str:
    """kebab-case slug: lowercase ASCII, non-alnum -> '-', max 60 chars at word boundary."""
    s = text.strip().lower()
    s = s.encode("ascii", "ignore").decode("ascii")  # drop non-Latin
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > 60:
        s = s[:60].rsplit("-", 1)[0]
    return s or "research"


def short_title(text: str, limit: int = 72) -> str:
    """A concise human title from a long topic/question — first sentence, capped.
    Used only as a fallback; the command normally passes an explicit --title."""
    s = " ".join(text.strip().split())
    for sep in ("? ", ". ", "! "):
        if sep in s:
            first = s.split(sep, 1)[0]
            if len(first) <= limit:
                return first
            break
    if len(s) <= limit:
        return s
    return s[:limit].rsplit(" ", 1)[0] + "…"


def host_of(url: str) -> str:
    try:
        h = urlparse(url).hostname or "source"
    except ValueError:
        h = "source"
    return h.replace("www.", "").strip(".") or "source"


def dump_frontmatter(fields: dict) -> str:
    """Render a YAML frontmatter block (key order preserved)."""
    body = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{body}---\n"


def highest_confidence(findings: list[dict]) -> str:
    ranks = [CONF_RANK.get(f.get("confidence", "low"), 2) for f in findings]
    if not ranks:
        return "none"
    return {0: "high", 1: "medium", 2: "low"}[min(ranks)]


# ─────────────────────────── vault scaffolding ───────────────────────────

def ensure_topic_vault(root: Path, slug: str, vault_title: str, purpose: str, today: str) -> Path:
    """Create research/<slug>/ (overview.md, CLAUDE.md, .obsidian/) if missing."""
    vault_dir = root / RESEARCH_NAMESPACE / slug
    if vault_dir.exists():
        return vault_dir

    vault_dir.mkdir(parents=True)          # also creates the research/ namespace dir
    (vault_dir / ".obsidian").mkdir()

    overview = (TEMPLATES_DIR / "research-topic-overview.md").read_text(encoding="utf-8")
    overview = overview.replace("<vault-slug>", slug)
    overview = overview.replace("<vault-title>", vault_title)
    overview = overview.replace("  <purpose>", textwrap.indent(purpose.strip(), "  "))
    overview = overview.replace("<YYYY-MM-DD>", today)
    (vault_dir / "overview.md").write_text(overview, encoding="utf-8")

    claude = (TEMPLATES_DIR / "research-topic-CLAUDE.md").read_text(encoding="utf-8")
    claude = claude.replace("<vault-title>", vault_title)
    (vault_dir / "CLAUDE.md").write_text(claude, encoding="utf-8")

    print(f"Scaffolded {RESEARCH_NAMESPACE}/{slug}/ (overview.md, CLAUDE.md, .obsidian/)")
    return vault_dir


def bump_updated(vault_dir: Path, today: str) -> None:
    """Set overview.md's `updated:` to today (the vault-level staleness signal),
    inserting it right after `created:` if absent. Line-level edit — the rest of
    the frontmatter is left untouched."""
    overview = vault_dir / "overview.md"
    if not overview.exists():
        return
    lines = overview.read_text(encoding="utf-8").splitlines(keepends=True)
    out, done = [], False
    for line in lines:
        if not done and re.match(r"^updated:\s", line):
            out.append(f"updated: {today}\n")
            done = True
        else:
            out.append(line)
    if not done:  # no updated: line yet — insert after created:
        rebuilt = []
        for line in out:
            rebuilt.append(line)
            if not done and re.match(r"^created:\s", line):
                rebuilt.append(f"updated: {today}\n")
                done = True
        out = rebuilt
    overview.write_text("".join(out), encoding="utf-8")


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

    fm = dump_frontmatter({
        "title": title or "Untitled research",
        "type": "research-report",
        "date": today,
        "confidence": highest_confidence(findings),
        "question": question,
        "sources": len(sources),
        "confirmed": len(findings),
        "tags": [],
    })

    blocks: list[str] = []
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

    fm = dump_frontmatter({
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
    question = data.get("question", "").strip()
    sources = data.get("sources", []) or []

    fm = dump_frontmatter({
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
        # web-x deep-read only for sources the native fetch skimmed; link the
        # raw note by its bare stem so vault-view + Obsidian both resolve it.
        raw = f"[[{host_of(url)}]]" if url in enriched else "—"
        parts.append(f"| {url} | {quality} | {claims} | {angle} | {raw} |")
    return "\n".join(parts).rstrip() + "\n"


def render_raw(url: str, markdown: str, today: str) -> str:
    fm = dump_frontmatter({
        "title": host_of(url),
        "type": "raw-source",
        "source": url,
        "date": today,
        "tags": [],
    })
    return fm + "\n" + (markdown or "").strip() + "\n"


# ─────────────────────────── main ───────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a deep-research run into a research topic vault.")
    parser.add_argument("--input", required=True, help="Path to the deep-research run JSON.")
    parser.add_argument("--vault-slug", required=True, dest="vault_slug",
                        help="Topic vault slug under research/ (e.g. local-llms).")
    parser.add_argument("--title", required=True, help="Short human title for the run's report + run-folder slug.")
    parser.add_argument("--vault-title", dest="vault_title", default=None,
                        help="Display title for a NEW topic vault's overview. Default: derived from --vault-slug.")
    parser.add_argument("--vault-purpose", dest="vault_purpose", default="TODO: describe this research topic.",
                        help="One-line purpose for a NEW topic vault's overview.")
    parser.add_argument("--root", default=None, help="Federation root. Default: ~/knowledge-vaults/")
    parser.add_argument("--enriched", default=None, help="Path to {url: raw_markdown} JSON from web-x.")
    args = parser.parse_args()

    slug = slugify(args.vault_slug)
    title = args.title.strip()
    vault_title = args.vault_title.strip() if args.vault_title else slug.replace("-", " ").title()

    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error: cannot read run JSON at {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    enriched: dict = {}
    if args.enriched:
        try:
            enriched = json.loads(Path(args.enriched).read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError) as e:
            print(f"Error: cannot read enrichment JSON at {args.enriched}: {e}", file=sys.stderr)
            sys.exit(1)

    today = datetime.date.today().isoformat()
    root = Path(args.root).expanduser() if args.root else (Path.home() / "knowledge-vaults")

    vault_dir = ensure_topic_vault(root, slug, vault_title, args.vault_purpose, today)
    bump_updated(vault_dir, today)   # stamp the vault's staleness signal on every run
    run_dir = run_folder_path(vault_dir, today, slugify(title))
    run_dir.mkdir()

    (run_dir / "report.md").write_text(render_report(data, today, title), encoding="utf-8")
    (run_dir / "blueprint.md").write_text(render_blueprint(data, today, title), encoding="utf-8")
    (run_dir / "sources.md").write_text(render_sources(data, today, enriched, title), encoding="utf-8")

    raw_written = 0
    if enriched:
        raw_dir = run_dir / "raw"
        raw_dir.mkdir()
        for url, markdown in enriched.items():
            (raw_dir / f"{host_of(url)}.md").write_text(render_raw(url, markdown, today), encoding="utf-8")
            raw_written += 1

    print(f"Wrote research run to {run_dir}")
    print(f"  - report.md      ({len(data.get('findings', []) or [])} findings)")
    print(f"  - blueprint.md")
    print(f"  - sources.md     ({len(data.get('sources', []) or [])} sources)")
    if raw_written:
        print(f"  - raw/           ({raw_written} web-x-enriched)")
    print()
    print(f"View it: /vault-x:view {RESEARCH_NAMESPACE}/{slug}")


if __name__ == "__main__":
    main()
