# Knowledge Vaults — Federation Root

This directory is a federation of structured knowledge-base vaults, managed by the `vault-x` Claude Code plugin.

## Layout

```
~/knowledge-vaults/
├── CLAUDE.md               ← you are here (federation orientation)
├── <name>-vault/           ← curated top-level vaults
│   ├── overview.md         ← vault identity (machine-readable frontmatter)
│   ├── CLAUDE.md           ← per-vault write conventions for Claude
│   ├── .obsidian/          ← Obsidian recognition
│   └── <content>           ← whatever structure this vault uses
└── research/               ← namespace for /vault-x:research output
    └── <topic-slug>/       ← one topic vault per subject (same vault shape)
        └── YYYY-MM-DD-<query>/   ← one dated run per research question
```

A vault is any directory containing `overview.md` — flat (`goddard-vault`) or
namespaced (`research/local-llms`). Run folders have no `overview.md`, so they are
not themselves vaults.

## How vaults work

- Each vault is **self-describing** — purpose, scope, and write rules live inside that vault.
- Every file carries **YAML frontmatter** (schema declared per-vault in its `CLAUDE.md`).
- Files link via **`[[wiki-links]]`** — hermetic per vault (no cross-vault links).
- Tools walk the filesystem dynamically; nothing is pre-indexed. Don't look for a manifest.

## Working with vaults

| Action | Command |
|---|---|
| See all vaults with their purposes | `/vault-x:list` |
| Map a single vault's contents | `/vault-x:view <vault>` (path, e.g. `research/local-llms`) |
| Create a new vault | `/vault-x:create <name>` |
| Research a question into a topic vault | `/vault-x:research "<question>"` |

**To write into a vault:** read that vault's `CLAUDE.md` for its conventions, then write following the declared frontmatter schema and link practice.

**To understand a vault's scope:** start with its `overview.md`.
