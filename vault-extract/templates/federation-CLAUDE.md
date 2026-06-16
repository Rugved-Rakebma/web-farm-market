# Knowledge Vaults — Federation Root

This directory is a federation of structured knowledge-base vaults, managed by the `vault-x` Claude Code plugin.

## Layout

```
~/knowledge-vaults/
├── CLAUDE.md           ← you are here (federation orientation)
└── <name>-vault/       ← one or more vaults
    ├── overview.md     ← vault identity (machine-readable frontmatter)
    ├── CLAUDE.md       ← per-vault write conventions for Claude
    ├── .obsidian/      ← Obsidian recognition
    └── <content>       ← whatever structure this vault uses
```

## How vaults work

- Each vault is **self-describing** — purpose, scope, and write rules live inside that vault.
- Every file carries **YAML frontmatter** (schema declared per-vault in its `CLAUDE.md`).
- Files link via **`[[wiki-links]]`** — hermetic per vault (no cross-vault links).
- Tools walk the filesystem dynamically; nothing is pre-indexed. Don't look for a manifest.

## Working with vaults

| Action | Command |
|---|---|
| See all vaults with their purposes | `/vault-x:list` |
| Map a single vault's contents | `/vault-x:view <vault>` |
| Create a new vault | `/vault-x:create <name>` |

**To write into a vault:** read that vault's `CLAUDE.md` for its conventions, then write following the declared frontmatter schema and link practice.

**To understand a vault's scope:** start with its `overview.md`.
