# <vault-title> — Research Conventions

A research topic vault under the `research/` namespace, written by
`/vault-x:research`. Its identity is in `overview.md`. Contents are written
mechanically by `scripts/research-scaffold.py` — you normally don't hand-edit here.

## Layout

One folder per research run: `YYYY-MM-DD-<query-slug>/`

```
report.md      # synthesized, verified findings
blueprint.md   # how the question was decomposed and searched
sources.md     # source ledger — quality, claim count, enrichment status
raw/<host>.md  # web-x deep-reads, only for sources the native fetch skimmed
```

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

Hermetic **within each run folder** — `report.md` links to `[[sources]]`,
`[[blueprint]]`, and into `raw/`. Don't link across run folders or across vaults.

## Promotion

To turn a finding into durable knowledge, copy the distilled note into a curated
topic vault by hand and cite the source URL. Cross-vault wiki-links don't resolve.
