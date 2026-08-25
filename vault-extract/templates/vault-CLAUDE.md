# <vault-name> — Write Conventions

A **tier-1** vault at the `~/knowledge-vaults/` federation root — hand-maintained, and not
reproducible by any classifier's tooling. The `-vault` suffix is the tier-1 marker. Its
identity is in `overview.md`; the federation standard is in `~/knowledge-vaults/CLAUDE.md`.

When adding content to this vault, follow the rules below. Read `overview.md` first if you're unsure whether content belongs here.

## Frontmatter schema

Every file in this vault carries YAML frontmatter at the top. Schema:

```yaml
---
title:        # required
# Add more fields here when this vault's needs are clear.
# Common candidates: date, tags, source, author, status
---
```

Update this block once the schema settles for this vault. Remove the placeholder comments.

## Wiki-links

Hermetic — `[[note-title]]` resolves only within this vault. Never link across vaults.

A tier-1 vault may declare exceptions *within* itself here — for example, root-level
documents linking down into a subfolder to cite evidence, with no links back up. Write
the exception down before relying on it.

## File placement

Default: place new files at the vault root. Declare subdirs here as the vault grows —
each hand-maintained layer you add is part of what makes this a tier-1 vault, so name it
and say who maintains it.

## Provenance

Created by `/vault-x:create`. A vault that arrived here via `/vault-x:graduate` gets
`templates/graduated-vault-CLAUDE.md` instead, which carries the run-file schema it
inherited from its classifier.
