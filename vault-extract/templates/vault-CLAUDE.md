# <vault-name> — Write Conventions

When adding content to this vault, follow the rules below. This vault's identity (purpose, topics, audience) is in `overview.md` — read that first if you're unsure whether content belongs here.

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

Hermetic — `[[note-title]]` resolves only within this vault. Don't link across vaults.

## File placement

Default: place new files at the vault root. Declare subdirs here as the vault grows.
