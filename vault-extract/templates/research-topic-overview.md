---
name: <vault-slug>
purpose: |
  <purpose>
topics:
  - <vault-title>
domain: <classifier>
audience: self
status: active
language: en
source_kinds:
  - web search results
  - fetched sources
  - synthesized reports
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
---

# <vault-title>

Research on **<vault-title>**, produced by `/vault-x:research`. Each dated subfolder
`YYYY-MM-DD-<query-slug>/` is one self-contained investigation:

- `report.md` — synthesized, adversarially-verified findings with confidence + citations
- `blueprint.md` — how the question was decomposed and searched
- `sources.md` — every source, its quality, and whether web-x deep-read it
- `raw/` — full extractions for sources the native fetch skimmed

Vault-level `sources/` holds the deduped raw-source evidence library built by
`/vault-x:grow`, shared across all runs.

This is a **lab notebook, not curated knowledge** — a tier-2 vault under the
`<classifier>/` classifier. It stays there while the tooling can reproduce it; if it ever
acquires hand-maintained content that a re-run would destroy, it graduates to a tier-1
vault at the federation root via `/vault-x:graduate`. See `~/knowledge-vaults/CLAUDE.md`.
