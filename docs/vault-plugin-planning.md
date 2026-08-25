# Vault Plugin — Planning & Alignment

> Living doc tracking design for the second plugin in `web-farm-market`. Status: **shipped; the v1 surface below is superseded in part by the two-tier standard — see the 2026-08-25 entry in the decisions log**.

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

> **Superseded in part.** This section describes the pre-tier v1 shape. `<name>-vault/` is now
> specifically **tier 1**, `list` does a bounded two-level scan rather than globbing
> `<federation>/*/overview.md`, and the surface has grown to seven commands. See the
> 2026-08-25 decisions-log entry.

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

### 2026-07-02 (research command — deep-research integration)

- **New command `/vault-x:research "<question>"`.** Fifth command in `vault-x`. Turns research into persistent, wiki-linked vault knowledge instead of a throwaway report. Extends this plugin — **no separate `search-x` plugin.**
- **Reuse the native `deep-research` workflow; don't rebuild it.** Anthropic ships it bundled in the CLI binary, invoked via `Workflow({name:"deep-research", args})`. We inherit its fan-out search / adversarial verification / cited synthesis — and its future improvements — for free. Verified from the binary: it **returns structured JSON** (`{question, summary, findings[], caveats, openQuestions[], sources:[{url, quality, angle, claimCount}], stats}`) to the caller, which is what makes the wrap possible.
- **`web-x` role = enrich the sources deep-research skimmed.** Its Fetch phase uses shallow `WebFetch`; video/JS/paywalled sources come back `claimCount == 0` but stay listed in `sources[]`. The command deep-reads exactly those URLs via `web-x:web`. **v1 trigger: `claimCount == 0` only** (no host allowlist). web-x does NOT nest inside deep-research — enrichment is strictly post-hoc.
- **Main-loop only.** `Workflow` is unavailable inside subagents, so `research` must run at top level and never be delegated. Dictates the form: a command orchestration recipe (`commands/research.md`) + a deterministic writer script (`scripts/research-scaffold.py`). No LLM in the file-writing step.
- **`research-vault` = standardized federation member.** Auto-created at `~/knowledge-vaults/research-vault/` on first run, from dedicated templates. Shows in `list`, maps via `view`. Each run is a dated folder `YYYY-MM-DD-<slug>/` with `report.md` / `blueprint.md` / `sources.md` / `raw/`. Hermetic wiki-links within a run. It's a **lab notebook**, not curated knowledge.
- **`blueprint.md` reconstructs angle *labels* only.** The harness returns angle labels per source (`sources[].angle`) but not the exact queries — acceptable for v1.
- **Intra-run links use bare wiki-links; single-run graph is clean.** `report.md → [[sources]], [[blueprint]]`; `sources.md → [[<host>]]` for each web-x-enriched raw note (bare stem so both `vault-view` and Obsidian resolve it — no aliased pipe inside table cells). **Known v1 limitation:** `vault-view` resolves links by basename, so across *multiple* runs the repeated `report`/`sources`/`blueprint` stems collide (run B's `[[sources]]` resolves to run A's). Single-run views are correct — the dominant early case. Revisit (path-qualified links or per-run stems) if multi-run archives make the collision bite.
- **Ephemeral research stays served by calling `deep-research` directly.** No vault machinery when you don't want a vault. Clean product boundary.
- **Explicitly deferred:** promotion/distillation of findings into topic vaults (manual for now), cross-run dedup, any index/search, host-allowlist enrichment triggers, an auto-triggering `skills/research/SKILL.md` (command-only for v1).

### 2026-07-03 (research namespace + always-prompt routing)

- **Per-topic research vaults under a `research/` namespace.** The flat single `research-vault/` (all runs, any subject) was wrong. New model: `~/knowledge-vaults/research/<topic-slug>/` — one topic vault per subject, each accumulating dated run folders `YYYY-MM-DD-<query-slug>/`. `research/` is a plain namespace directory, not a vault.
- **Two slugs, separated.** The *topic* names the vault (short clean slug, e.g. `local-llms`, **no `-vault` suffix** — the namespace already says what it is); the *query* names the dated run folder (`--title` → slug). `research-scaffold.py` gained `--vault-slug` / `--vault-title` / `--vault-purpose`, dropped `--topic`.
- **Always-confirm routing.** A run costs ~2M tokens / ~10 min, so `/vault-x:research` **always** asks (`AskUserQuestion`, recommendation pre-selected) which topic vault to target — existing match or a new clean slug — *before* running the harness. Never silent-route.
- **Topic granularity defaults broad.** Fold related queries into one topic vault; the prompt catches genuine ambiguity.
- **Path-based vault identity.** A vault = any dir containing `overview.md`, named by its path relative to the root. `vault-list` discovers recursively; `vault-view` resolves by relative path → legacy `<name>-vault` → unique leaf. Legacy flat vaults keep working; run folders (no `overview.md`) are never mistaken for vaults.
- **Folder-relative link resolution.** `vault-view` now prefers a same-directory target when resolving `[[stem]]`, so each dated run's `[[sources]]`/`[[blueprint]]` links resolve within its own run folder even when a topic vault holds many runs with repeated stems. **Supersedes the cross-run basename-collision limitation** logged 2026-07-02.
- **Migration:** the one existing run moved from `research-vault/` → `research/local-llms/` (fresh topic overview; run folder + its 2026-07-02 date preserved).

### 2026-07-03 (`/vault-x:grow` — vault maturation; timestamp foundation)

- **Staleness foundation first.** Every run file carries `date` (when researched); topic `overview.md` carries `created` + `updated`, and the scaffolder **bumps `updated` on every run**. `/vault-x:list` surfaces Created·Updated. `CLAUDE.md` stays prose-only (meta file). This is the substrate a future refresh process needs — built before enrichment.
- **`grow` is separate from `research`, by design.** `research` is atomic (one question → one run). `grow` is a **vault-level maturation** pass over an existing topic vault. Baking maturation into every research call would conflate "add a data point" with "mature the whole corpus" and explode per-call cost.
- **A-after-B (depth after breadth).** `grow` runs breadth (gap research) *then* depth (source enrichment). Enriching after breadth lets sources be ranked by **cross-run** importance (cited by many runs × quality) and deduped — strictly better than per-run enrichment, which can't see across runs.
- **Vault-level `sources/` evidence library.** Enriched raw text lives at `research/<slug>/sources/` (deduped, URL-derived slug, stamped `published`/`retrieved`/`cited_by`), not per-run `raw/`. Turns a topic vault into two layers: **runs = analysis**, **sources/ = evidence**. Written by the standalone `research-source.py`.
- **One pipeline, confirm checkpoints.** `grow` = Assess → propose breadth (`AskUserQuestion`, cost-flagged) → research gaps → enrich top-K → report. Checkpoints give separability for free (bail after assess; pick no gaps → enrich-only). `vault-list`/`vault-view` unchanged — `sources/` has no `overview.md` so it's never mistaken for a vault.
- **`research` keeps only its `claimCount==0` self-heal.** All deliberate depth moved to `grow`.
- **Deferred:** run→`sources/` back-linking; per-run machine-readable sources sidecar; a `## Runs` index in overview; staleness *refresh* (grow's future phase); promotion into curated vaults (avenue C).

### 2026-07-04 (fork deep-research — supply angles ourselves)

- **The native Scope agent aborts runs.** Anthropic's bundled `deep-research` starts with a single Scope agent that must emit the pipeline's most complex structured output (question + 5 angle objects). The model intermittently slips JSON↔XML tool-call encodings, fails the 5-strike `StructuredOutput` cap, and **throws** — killing the whole ~2M-token run at its non-redundant root step. Observed 2/2 on a real run (and once on the original local-llms run).
- **Fix: supply the angles ourselves; skip the Scope agent.** New `vault-extract/workflows/deep-research-local.js` — a fork of the native script with the Scope agent removed; the main loop (which emits valid structured output reliably) generates the 5 `{label, query}` angles and passes them via `args`. Everything downstream (dedup, 3-vote verify, synthesize, return shape) is byte-identical, so `research-scaffold.py` + the synthesis-check are unchanged. Launched via `Workflow({scriptPath, args:{question, angles, caps?}})`.
- **Opus was already in play.** The native script sets **no** per-agent model, so subagents inherit the session model — which is Opus 4.8. The flakiness is Opus's; pinning `model:'opus'` in the fork is a *guarantee* (and survives a non-opus session), **not** the cure. The cure is removing the Scope agent.
- **`args` normalization.** The harness may deliver `args` as an object or a JSON string; the fork normalizes once at the top (parse-if-string) before reading `caps`/`question`/`angles`. `caps` also lets a tiny smoke run validate the JS cheaply (~13 agents).
- **Validated:** smoke run (tiny caps) cleared Scope, ran 13 agents, returned a well-formed report with real synthesis. `research.md`/`grow.md` updated to generate angles + launch the fork.
- **Deferred:** in-fork synthesis hardening (the command already reconstructs from transcript); a re-sync routine for Anthropic's deep-research updates; per-phase cheaper models if opus cost bites.

### 2026-08-25 (the two-tier standard + `/vault-x:graduate`)

- **Two tiers, and the path declares which.** `~/knowledge-vaults/` holds exactly two kinds of vault. **Tier 1** — `<name>-vault/` at the root: graduated, hand-maintained, not reproducible by tooling. **Tier 2** — `<classifier>/<slug>/`: machine-produced, owned by the classifier's tooling, slug carries **no** `-vault` suffix. The rule is biconditional: a `-vault` suffix means tier 1; membership in a classifier means tier 2; never both. `research/` is the only classifier, and a new one is justified only by a genuinely different **kind** of vault with its own generator — never to sub-categorise topics. That is what the slug is for.
- **`<name>-vault` is tier 1, not legacy.** **Supersedes 2026-07-03's "Path-based vault identity"**, which framed flat `<name>-vault/` dirs as back-compat that "keeps working". They are the top tier and the destination of graduation. Path-based identity itself stands, and is now the mechanism by which tier is read — but **narrowed**: a vault is an `overview.md` at exactly one of two positions. Discovery is a bounded two-level `iterdir()`, not `rglob`, so an `overview.md` at depth 3+ is vault content rather than a phantom vault at no tier.
- **`research/` is a classifier, not a namespace.** **Refines 2026-07-03.** The directory groups vaults by *how they are made*, and its tooling owns everything inside. Classifier is now a real parameter — `--classifier`, default `research` — rather than a constant. The no-suffix-inside-the-classifier rule from that entry stands and is now half of the biconditional above. A classifier that doesn't exist requires `--allow-new-classifier`, so a typo can't fork the federation.
- **The graduation test.** *Could a fresh run of the classifier's tooling reproduce this vault?* If **no** — it holds private records, live decision documents, or distilled positions that must survive a re-run — it belongs at tier 1. That is the only criterion. Size, importance, and age are not criteria.
- **Graduation is a move, not a copy.** **Supersedes the deferred "promotion/distillation of findings into topic vaults"** (2026-07-02) and "promotion into curated vaults (avenue C)" (2026-07-03). Both modelled the upward path as hand-copying *findings* out of the lab notebook into some curated vault. Wrong shape: the vault itself is what matures. Graduation is `git mv <classifier>/<slug> <name>-vault` + a rewrite of `CLAUDE.md` (it declares its own layers now, not the classifier's) + an `overview.md` update (`domain:` moves off the classifier). One-way. Nothing is copied and nothing is left behind.
- **A tier-1 vault still receives tooling.** `/vault-x:research` and `/vault-x:grow` both target either tier, **implicitly** — no opt-in flag; the always-confirm step in the command layer is the gate. What graduation changes is **ownership**, not access: the classifier's tooling no longer owns the vault's shape, and hand-maintained layers win over any single run. **Supersedes 2026-07-02's `research-vault` entry**, which assumed one auto-created vault as the sole destination of every run.
- **Auto-create is tier-2-only.** Tooling may materialise `<classifier>/<slug>/`; it may never materialise `<name>-vault/`. Tier 1 is a human act (`create`) or a graduation. "The tool silently created a tier-1 vault" is now structurally impossible.
- **A stale reference is a hard error, never a silent redirect.** After `research/local-llms` graduates, `--vault research/local-llms` exits 5 naming the tier-1 home, with the corrected command in the hint. Considered and rejected: following `graduated_from:` automatically. A ~2M-token run must not land somewhere the user didn't name.
- **`/vault-x:graduate` = script moves, Claude writes.** `scripts/vault-graduate.py` does the deterministic half — validate, audit, rewrite `overview.md` frontmatter, drop the tier-1 `CLAUDE.md` template with marker blocks, `git mv`. Claude fills the markers, because only it knows what the vault earned. Same deterministic-writer / LLM-judgement split as `research`.
- **The audit is a necessary condition, not the test.** The script can't judge reproducibility, but it can enumerate what the classifier's tooling could not have written (anything that isn't `overview.md`/`CLAUDE.md`/`.obsidian/`/`sources/`/a dated run folder holding only the four known files). Empty set → refuse. Sufficiency is Claude's call, confirmed via `AskUserQuestion`. Verified: the audit refuses `research/local-llms` (5 runs + `sources/`, fully reproducible) and surfaces exactly `records/`, `advisor-packet/`, `playbook.md`, `colombia-relocation-brief.md`, `colombia-travel-log.md` in `personal-tax-vault`.
- **Git: detect the tracking repo, never hardcode it.** The federation is tracked by a **bare** repo (`~/.home-env-git.git`, `--work-tree=$HOME`, the `henv` alias), so a plain `git mv` inside `~/knowledge-vaults` fails — no `.git` in the ancestry. Resolution order: explicit flags → env vars → ordinary repo via `rev-parse --show-toplevel` → **probe bare repos in `$HOME` and adopt the one whose `ls-files` tracks the source path** → `shutil.move` + print the exact staging command. Never commits. `status.showUntrackedFiles=no` is set on that repo, so the clean-tree gate must pass `-uall` or it reads a dirty tree as clean.
- **Provenance in frontmatter, no tombstone.** Graduation writes `graduated:` and `graduated_from: <classifier>/<slug>`. A tombstone *directory* is wrong either way — with an `overview.md` it registers as a phantom vault in `list`; without one the walker can't see it. **No `tier:` key**: the path already declares it, and duplicating derivable state in the vault is the same mistake as `manifest.md`. History isn't derivable; tier is.
- **Shared `scripts/_common.py`.** Tier-aware resolution `(tier, classifier, slug, path, rel)`, `target_ref()`, bounded `discover()`, the never-both validator, frontmatter, and one uniform entrypoint — extracted from the copies scattered across all six scripts. The library **raises `VaultError` and never calls `sys.exit`**, which is what makes resolution composable. `vault-view`'s local `resolve_vault()` and both `RESEARCH_NAMESPACE` constants are retired. Exit codes: 1 general · 2 argparse · 3 not found · 4 ambiguous · 5 tier violation.
- **Bugs found and fixed while doing this.** (a) `resolve_vault`'s legacy `<name>-vault` branch short-circuited *before* the ambiguity guard, so a bare slug matching both tiers silently returned tier 1 and the guard never fired. (b) `ensure_topic_vault` checked one path, so the next run after a graduation silently re-scaffolded a duplicate. (c) `vault-create` had the same bug mirrored. (d) `research-scaffold.py` substituted only `<vault-title>`, so every tier-2 vault scaffolded since the template gained `research/<vault-slug>/` shipped an unreplaced placeholder. (e) two `slugify` implementations diverged (`naïve` → `nave` vs `na-ve`), which made `research-source.py` compute a different directory than the one `research-scaffold.py` created; unified on NFKD folding. (f) `raw/<host>.md` collided for two URLs on one host — now `source_slug` (host + path). (g) `bump_updated`'s regex wasn't scoped to the frontmatter block, missed `updated:2026-01-01`, and could double-insert. (h) excluded-dir filtering ran on absolute path parts. (i) absolute-path input escaped the root and crashed on `relative_to`.
- **Terminology, fixed.** Three words, three meanings. **Tiers** = the federation's two levels. **Layers** = the hand-maintained additions a tier-1 vault earned. **Tracks** = runs vs `sources/` inside one vault. **Amends 2026-07-03's "two layers: runs = analysis, sources/ = evidence"** — that is now "two **tracks**", because "layers" was needed for the tier-1 sense.
- **Deferred:** un-graduation (manual `git mv` back, by design); a second classifier; `--adopt` for vaults outside the root; auto-detecting graduation-readiness during `grow` (the audit exists, but proposing graduation unprompted is a step too far).

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
2. **`overview.md` template** — final frontmatter field list (current proposal is provisional). *Partly settled 2026-08-25: `graduated:` / `graduated_from:` are now written by `graduate`; a `tier:` key was considered and **rejected** — the path already declares tier.*
3. **`list` filter on `status`.** Hide `dormant`/`archived` by default? Show all? Flag-controlled?
4. **Graduation-readiness signal in `/vault-x:list`.** The reproducibility audit could run federation-wide and flag tier-2 vaults already holding unreproducible content. Cheap; unclear whether it's noise.

### Post-first-run fixes — APPLIED 2026-07-03
> From the first live `/vault-x:research` run (2026-07-02); batched and applied together. See `deep-research-harness.md` for run context.
1. **Synthesis-robustness (important).** ✅ `commands/research.md` step 3 now detects a degenerate native synthesis (placeholder summary / findings count far below `stats.confirmed`) and reconstructs the report from the `## Confirmed claims` block in the synthesize agent's transcript. (On the 2026-07-02 run this recovery was done by hand.)
2. **Title length (polish).** ✅ `research-scaffold.py` gained a `--title` arg (short label) for the frontmatter `title` of report/blueprint/sources; the full question stays in the `question` field + body H1. Falls back to a truncated `--topic` via `short_title()`.
3. **Question-length guidance.** ✅ `commands/research.md` step 1 now instructs condensing long/punctuation-heavy questions to ~100 words plain-ASCII before the `Workflow` call (attempt 1 failed when the Scope agent hit the structured-output retry cap).

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
