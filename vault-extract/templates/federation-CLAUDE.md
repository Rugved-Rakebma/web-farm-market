# Knowledge Vaults — Federation Root

A federation of structured knowledge-base vaults, managed by the `vault-x` Claude Code plugin.

## The two-tier standard

Every vault sits at exactly one tier. Its **path** declares which.

```
~/knowledge-vaults/
├── CLAUDE.md                     ← you are here (federation orientation)
│
├── <name>-vault/                 ← TIER 1 — graduated knowledge vaults
│   ├── overview.md               ←   vault identity (machine-readable frontmatter)
│   ├── CLAUDE.md                 ←   this vault's write conventions
│   ├── .obsidian/                ←   Obsidian recognition
│   └── <hand-maintained layers>  ←   whatever this vault has earned
│
└── <classifier>/                 ← TIER 2 — classified vaults, grouped by kind
    └── <slug>/
        ├── overview.md
        ├── CLAUDE.md
        ├── .obsidian/
        └── <tool-generated content>
```

**The rule:** a `-vault` suffix at the root means tier 1. A vault inside a classifier
directory is tier 2, and its slug carries **no** suffix — the classifier already names
its kind. Never both.

A vault is a directory containing `overview.md` **at exactly one of those two positions**:
`<name>-vault/` or `<classifier>/<slug>/`. An `overview.md` deeper than that is vault
content, not a vault — a vault at no tier is not a thing. Directories without an
`overview.md` (run folders, `sources/`, `records/`) are contents too.

Discovery is a bounded two-level scan, so tier and classifier are read off the position
rather than guessed. Nothing is pre-indexed and there is no manifest.

### Tier 2 — classified vaults

Machine-produced. A classifier directory groups vaults by **how they are made**, and its
tooling owns everything inside. Re-running that tooling reproduces the vault.

| Classifier | Produced by | Holds |
|---|---|---|
| `research/` | `/vault-x:research`, `/vault-x:grow` | `<slug>/YYYY-MM-DD-<query>/` runs + a deduped `sources/` evidence library |

`research/` is the only classifier today. Add another only when a genuinely different
**kind** of vault has its own generator — never to sub-categorise topics. Topic
separation is what the slug is for.

### Tier 1 — graduated knowledge vaults

Hand-maintained, and direct children of the root as `<name>-vault/`.

**The graduation test:** could a fresh run of the classifier's tooling reproduce this
vault? If **no** — because it now holds private records, live decision documents, or
distilled positions that must survive a re-run — it belongs at tier 1.

Graduating is a move plus a rewrite:

1. `git mv <classifier>/<slug> <name>-vault`
2. Rewrite `<name>-vault/CLAUDE.md` — it declares its own layers now, not the classifier's.
3. Update `overview.md` — move `domain:` off the classifier and describe the added layers.

Graduation is one-way. A tier-1 vault may still receive `/vault-x:research` runs, but the
classifier's tooling no longer owns its shape, and hand-maintained layers always win over
any single run.

## How vaults work

- Each vault is **self-describing** — purpose, scope, and write rules live inside it.
- Every file carries **YAML frontmatter**; the schema is declared in that vault's `CLAUDE.md`.
- Files link via **`[[wiki-links]]`**, hermetic per vault. Cross-vault links don't resolve.
- Nothing is pre-indexed. Walk the filesystem; don't look for a manifest.

## Working with vaults

| Action | Command |
|---|---|
| See all vaults with their purposes | `/vault-x:list` |
| Map a single vault's contents | `/vault-x:view <path>` (e.g. `research/local-llms`, `personal-tax-vault`) |
| Create a tier-1 vault | `/vault-x:create <name>` |
| Research a question into a tier-2 vault | `/vault-x:research "<question>"` |
| Mature a vault (breadth + depth) | `/vault-x:grow <vault>` |
| Graduate a tier-2 vault to tier 1 | `/vault-x:graduate <classifier>/<slug>` |

**To write into a vault:** read that vault's `CLAUDE.md` first, then follow its declared
frontmatter schema and link practice.

**To understand a vault's scope:** start with its `overview.md`.
