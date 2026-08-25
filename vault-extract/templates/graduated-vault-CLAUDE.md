# <vault-title> — Write Conventions

A **tier-1** vault at the `~/knowledge-vaults/` federation root, graduated out of the
`<classifier>/` classifier on `<YYYY-MM-DD>`. Its identity is in `overview.md`; the
federation standard is in `~/knowledge-vaults/CLAUDE.md`.

Dated run folders are still written mechanically by `/vault-x:research` and
`/vault-x:grow` — you normally don't hand-edit there. But the classifier's tooling
**no longer owns this vault's shape**: the hand-maintained layers below outrank any
single run, and nothing the tooling does may modify them.

<!-- vault-x:graduate:layers -->
## Layers

_Claude: replace this whole block, markers included. Only you know what this vault
earned. State each of the following:_

1. _**What each hand-maintained layer is** and who maintains it (you, not the tooling)._
2. _**Which parts the classifier's tooling still writes**, and that it no longer owns
   the vault's shape._
3. _**Frontmatter `type:` values** for the hand-maintained files — extend the run-file
   schema below, don't replace it._
4. _**Wiki-link practice**, if this vault now links across folders._
5. _**Anything sensitive** this vault holds, where it lives, and where it may not go._

_The graduation audit found these entries the `<classifier>/` tooling could not have
produced. They are your raw material:_

<unreproducible-list>

_`~/knowledge-vaults/personal-tax-vault/CLAUDE.md` is the worked example of all five._
<!-- /vault-x:graduate:layers -->

## Layout

```
<layout-tree>
```

## Frontmatter schema (`report.md`)

Carried over from the `<classifier>/` classifier — dated runs still use it:

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

Supporting run files use `type: research-blueprint`, `source-ledger`, `raw-source`.
Hand-maintained files in this vault should declare their **own** `type:` values —
add them in the Layers block above as they appear.

## Wiki-links

Run folders are **hermetic** — `report.md` links to `[[sources]]`, `[[blueprint]]`, and
into `raw/`. Don't link from one run folder into another, and never across vaults.

Root-level hand-maintained documents are the exception a tier-1 vault may declare: they
may link to each other and **down** into a run's report to cite the evidence behind a
position. Runs never link back up. Declare the exact practice in the Layers block once
this vault's root documents exist.
