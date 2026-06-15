# Vault Plugin — Planning & Alignment

> Living doc tracking design for the second plugin in `web-farm-market`. Status: **v1 surface defined; aligning on details before code**.

## How to use this doc

- **Decisions log** is append-only. Once we agree, it goes there with a date.
- Other sections reflect *current* state and get rewritten as understanding sharpens.
- **Open questions** at the bottom queues the next round.

---

## Working definition

A Claude-Code plugin that operationalizes the **knowledge-base vault pattern** already prototyped at `/Users/rugvedambekar/Code/manifested/knowledge-vaults/`. The plugin is the **tool layer over a federation of structured vaults** — it doesn't reinvent the storage pattern; it makes the pattern operable by Claude across the federation.

Scope: structured corpus-vaults (each a folder under a federation root, conforming to a frontmatter contract + controlled vocab + write conventions). NOT arbitrary existing Obsidian vaults — those are out of scope or get adopted later.

---

## Primary reference: the existing `knowledge-vaults/` pattern

Already in place at `~/Code/manifested/knowledge-vaults/`:

- **Federation root** with contract docs: `SCHEMA.md` (universal frontmatter), `CONCEPTS.md` (per-corpus controlled vocab), `INGESTION.md` (build pipelines), `README.md` (orientation)
- **Tools** in `tools/`: `extract_chapters.py`, `migrate_chapter_metadata.py`, `validate_chapters.py`, `validate_migration.py`
- **Recipes** in `justfile`: `kb-extract`, `kb-migrate`, `kb-validate`, `kb-reload`
- **Cache invalidation** primitive: `.vault-mtime` marker file
- **Subagents** (in sibling `manifested-reality-agent/.claude/agents/`): `book-skeleton-builder`, `chapter-extractor`, `book-index-reviewer`, `lecture-enricher`
- **Corpus today:** `goddard-vault/` (13 books · 140 chapters · 238 lectures · 28 vocab slugs)

This is v0 of what we're scaling. The plugin doesn't invent a new pattern — it generalizes this one for federation-scale Claude operation.

---

## Architecture principle: data vs process

The core inversion:

| Layer | Holds |
|---|---|
| **Vault** | DATA — source files with standardized frontmatter, plus `CLAUDE.md` files at write-points that teach Claude the local writing conventions. **Nothing else.** |
| **Tools** (CLI/MCP) | PROCESS — walk the filesystem on demand, parse frontmatter, produce navigable maps and search results. Dynamic; no static metadata. |

**Implication:** no `manifest.md`, no per-dir `index.md`. Those would be metadata-about-the-vault stored *in* the vault — drift-prone, stale-prone, redundant. The tool produces the equivalent dynamically each call.

Two clean surfaces:
- **Write side** = `CLAUDE.md` in-vault (write-conventions prose for Claude) + `overview.md` (machine-readable vault identity) → governs *how new content gets added and how the vault describes itself*
- **Read side** = tool layer → governs *how Claude finds and navigates*

Karpathy's "wiki" layer maps to what the tool *outputs*, not what's stored.

### The substrate the tools rely on

Two things must be present on every file for the tool layer to work:

1. **Frontmatter** — YAML at the top of every file. Schema is per-vault (declared in that vault's `CLAUDE.md`); the universal property is *that it exists and parses*. Tools parse on demand.
2. **Wiki-links** — files reference each other via `[[note-name]]`. Tools walk this graph to surface forward links, backlinks, and orphans.

The combination turns a folder of markdown into a navigable knowledge graph. Without frontmatter, no machine-readable identity per file. Without wiki-links, no relational structure. The tools depend on both.

---

## v1 operation surface (minimal)

Four commands. Read-side first; write happens via Claude editing files directly, guided by the in-vault `CLAUDE.md`.

Plugin slash prefix: `/vault-x:` (matching the `web-x` convention).

### `init`
Bootstrap the federation root. Once per machine, typically.

Scaffolds:
- `~/knowledge-vaults/` (default; overridable via `--root` flag or env var)
- `CLAUDE.md` at federation root with one-paragraph orientation + brief guidance for how `create` / `list` / `view` are used

### `create <name>`
Bootstrap a new vault inside the federation.

Scaffolds:
- `<federation>/<name>-vault/`
- `<vault>/overview.md` — frontmatter template + body prompts (the `list`-aggregation source)
- `<vault>/CLAUDE.md` — write-conventions template (including a place to declare per-vault frontmatter schema and wiki-link conventions)
- `<vault>/.obsidian/` — minimal config; user opens in Obsidian once to register

**Does NOT** pre-impose `source/` or any subdirs — those are vault-specific decisions when the vault is designed.
**Does NOT** programmatically edit Obsidian's `obsidian.json`.

Inputs: name + purpose (interactive prompt, or `--purpose` flag).

### `list`
Federation overview, optimized for **vault selection** by Claude.

Walks `<federation>/*/overview.md`, reads frontmatter, returns one row per vault.

Surfaces (whichever fields the vault declares): name, path, purpose, topics, domain, audience, status, language, size signal.

### `view <vault>`
Single-vault map, optimized for **file selection** by Claude.

Walks the vault and produces:
- dir tree
- per-file frontmatter highlights (whatever schema this vault uses)
- wiki-link graph: forward links, backlinks; flag orphan files

### `overview.md` frontmatter template

Scaffolded by `create`. Filled in interactively or post-hoc.

```yaml
---
name: <vault-name>
purpose: |
  One paragraph. What this vault is for.
topics:
  - topic 1
  - topic 2
domain: <e.g. psychology / engineering / cooking>
audience: <self | team | public>
status: active     # active | dormant | archived
language: en
source_kinds:      # what types of content live here
  - books
  - lectures
created: <YYYY-MM-DD>
---

# <Vault Name>

Longer human-readable overview: history, examples, anything authored.
```

**Explicitly deferred from v1:** `search`, `validate`, `suggest`, `ingest`, `get`, `vocab`, `stats`, destructive ops, MCP server. Add when the gap is felt.

---

## Decisions log

> Append-only. Date format: YYYY-MM-DD.

### 2026-06-11 (architectural forks)

- **Fork 3 — vault model: federated with intelligent suggestion.** User creates/picks vaults; Claude suggests based on work context + known vaults; plugin tracks the set. Vault creation is a first-class tool-surface operation.
- **Fork 4 — authority: autonomous, safety from tool surface.** Claude is autonomous; safety comes from clean, atomic, reversible-by-default tools — not from Claude restraint. Sub-question opened: MCP vs slash commands vs both.
- **Fork 5 — retrieval: in scope for v1.** Vaults are knowledge bases — retrieval and navigation are core, not deferrable.
- **Fork 1 — structure: scaffolded with meaningful folders** (tentative at time of decision; closed below).

### 2026-06-11 (after digesting Karpathy gist + obsidian-llm-wiki plugin + existing `knowledge-vaults/`)

- **Data vs process inversion.** Vault holds data + write-side guidance only. Tool layer holds the process. No `manifest.md`, no per-dir `index.md` — both replaced by dynamic tool output.
- **Karpathy + obsidian-llm-wiki + existing `knowledge-vaults/`: references only, NOT blueprints.** Their concepts inform v2; their files are not v2 artifacts. The plugin doesn't ship `SCHEMA.md` / `CONCEPTS.md` / `INGESTION.md` — those were Goddard-specific instantiations.

### 2026-06-15 (naming)

- **Plugin slug: `vault-x`** (drives slash prefix `/vault-x:`). Matches the `web-x` convention.
- **Plugin directory: `vault-extract/`** in the repo root. Mirrors `web-extract/`.

### 2026-06-15 (output, links, scope)

- **Output format: structured markdown.** No JSON flag for MVP. Claude reads markdown natively; humans read the same output in terminal. One format, no parser.
- **Wiki-links: hermetic per vault.** `[[note]]` resolves only within its own vault. Each vault is its own graph. No cross-vault link resolution in MVP. Revisit if a clear cross-vault use case emerges.
- **Empty-vault `view`: returns `overview.md` + scaffold tree + "no content yet" marker.** Clear signal that the vault exists but is empty.
- **Existing arbitrary vaults outside `~/knowledge-vaults/`: out of scope for MVP.** No `--adopt` path. Existing vaults (`research-vault`, `Recirq`, etc.) stay untouched. Revisit after MVP works.

### 2026-06-11 (cont. — final v1 shape)

- **Architecture: CLI + slash commands** (matching `web-extract`). Python scripts + slash-command wrappers via Bash. Defer MCP until Bash overhead is felt.
- **Federation root: `~/knowledge-vaults/`.** Hardcoded default, overridable via `--root` flag or env var. This is a new canonical location, distinct from any existing project folder.
- **v1 surface: `init`, `create`, `list`, `view`.** Four commands. Slash prefix: `/vault-x:`.
- **No universal frontmatter contract.** Each vault declares its own schema in its `CLAUDE.md`. Tools parse whatever frontmatter is present.
- **The substrate the tools rely on: frontmatter + wiki-links.** Every file carries parseable YAML frontmatter (per-vault schema). Files reference each other via `[[wiki-links]]`. The combination is what makes a vault a navigable knowledge graph the tools can expose. Both must be present.
- **`overview.md` per vault** — separate from `CLAUDE.md`. Holds machine-readable identity (rich frontmatter aggregated by `list`); body is human prose. Distinct from rejected `manifest.md` because identity is authored, not derivable.
- **`CLAUDE.md` scope clarified:** write-side guidance ONLY (prose for Claude — frontmatter schema declaration + wiki-link conventions). Identity → `overview.md`. Two files, two roles.
- **`create` does NOT pre-impose subdirs** (`source/`, `reviews/`, etc.). Those are vault-specific decisions made when the vault is designed.
- **`create` does NOT programmatically register the vault with Obsidian's `obsidian.json`** — user opens once in Obsidian to register. Avoids brittleness.

---

## Resolved tensions

| Fork | Resolution |
|---|---|
| **1** structure | ✅ No imposed structure beyond `<vault>/{overview.md, CLAUDE.md, .obsidian/}`. Each vault decides its own internal layout, declared in its `CLAUDE.md`. |
| **2** capture vs curation | ✅ Curation-first — every new file gets frontmatter at write time. Per-vault `CLAUDE.md` declares the schema. |
| **3** vault model | ✅ Federated. v1 supports `init` + `create` + `list` + `view`. |
| **4** authority | ✅ Autonomous Claude, safety via tool design. **Tool surface: CLI + slash commands for MVP.** MCP deferred. |
| **5** retrieval | ✅ In scope for v1. Mechanism: filesystem walk + frontmatter parse + wiki-link graph traversal. No embeddings, no static indexes. |

---

## Open questions

### Active design questions
1. **`CLAUDE.md` template content** — concrete sections, examples, verbosity for both the federation-root and per-vault flavors.
2. **`overview.md` template** — final frontmatter field list (current proposal is provisional).
3. **`list` filter on `status`.** Hide `dormant`/`archived` by default? Show all? Flag-controlled?

### Deferred (revisit post-MVP)
- Privacy boundaries (Claude-read/write per vault)
- Sync behavior (Obsidian Sync / iCloud / git interactions)
- `create --adopt <path>` for existing vaults

---

## Prior art

| Source | Why | Status |
|---|---|---|
| **`~/Code/manifested/knowledge-vaults/`** | Primary reference. The v0 pattern this plugin scales. SCHEMA / CONCEPTS / INGESTION / tools. | ✅ read |
| **Karpathy's LLM Wiki gist** | Conceptual ancestor — three-layer architecture (sources / LLM-maintained wiki / schema-as-CLAUDE.md). Inspiration, not blueprint. | ✅ read |
| **obsidian-llm-wiki plugin** (Greener-Dalii) | One mature Karpathy instantiation. Innovations worth borrowing: lint causality order, alias-aware dedup, tag-vocabulary control, reviewed-guard. | ✅ surveyed |
| LYT Kit, Andy Matuschak, PARA, Johnny Decimal | General PKM patterns. Less relevant now that we've anchored on the existing pattern. | 🟡 deferred |

---

## Next-step process

1. Decide **output formats** for `list` and `view` (markdown vs JSON).
2. Sketch the concrete `CLAUDE.md` template for new vaults.
3. Sketch the concrete `overview.md` template (frontmatter fields + body prompts).
4. Sketch the federation-level `CLAUDE.md` (what `init` writes).
5. Sketch tool implementations — signatures, output shapes, file walking strategy.
6. Name the plugin (internal package/dir name).
7. Build v1.
