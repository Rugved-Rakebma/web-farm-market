# <vault-title> — Research Conventions

A **tier-2** vault under the `<classifier>/` classifier, at `<classifier>/<vault-slug>/`. Its
identity is in `overview.md`; the federation standard is in `~/knowledge-vaults/CLAUDE.md`.
Contents are written mechanically by `/vault-x:research` and `/vault-x:grow` — you
normally don't hand-edit here.

## Layout

```
overview.md                  # vault identity
CLAUDE.md                    # this file
<YYYY-MM-DD-query-slug>/     # one research run each
  report.md                  #   synthesized, verified findings
  blueprint.md               #   how the question was decomposed and searched
  sources.md                 #   source ledger — quality, claim count, enrichment status
  raw/<host>.md              #   web-x deep-reads, only where the native fetch skimmed
sources/                     # deduped raw-source evidence library, built by /vault-x:grow
```

`sources/` is vault-level and shared across runs — one note per unique URL, stamped with
`published` / `retrieved` / `cited_by`. Run folders are per-question and self-contained.

## Frontmatter schema (`report.md`)

```yaml
---
title:        # short label for the run
type: research-report
date:         # YYYY-MM-DD of the run
confidence:   # high | medium | low — highest among the findings
question:     # verbatim research question
sources:      # count of sources fetched
confirmed:    # count of verified findings
tags: []
---
```

Supporting files use `type: research-blueprint`, `source-ledger`, `raw-source`.

## Wiki-links

Hermetic **within each run folder** — `report.md` links to `[[sources]]`, `[[blueprint]]`,
and into `raw/`. Don't link across run folders or across vaults.

## Graduation

This vault stays tier 2 for as long as `/vault-x:research` and `/vault-x:grow` can
reproduce it. The moment it acquires hand-maintained content they can't regenerate —
private records, a live decision document, a distilled position — it graduates to a
tier-1 vault at the federation root:

```
/vault-x:graduate <classifier>/<vault-slug>
```

See the graduation test in `~/knowledge-vaults/CLAUDE.md`. Graduation is one-way.
