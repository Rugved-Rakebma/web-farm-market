# Vault Extract — Development Guide

## Architecture

Manages a federation of structured knowledge-base vaults at `~/knowledge-vaults/`. Plugin slug `"vault-x"` creates the `/vault-x:` prefix.

Two layers:

1. **Commands** (`/vault-x:*`) — User-invocable workflows in `commands/`. Most call a Python script via `${CLAUDE_PLUGIN_ROOT}/scripts/`; `research` instead orchestrates other tools in the main loop (see below).
2. **Scripts** — Python orchestration in `scripts/`. Read template files from `templates/` at scaffold time.

## Plugin Structure

```
commands/               # /vault-x:init, /vault-x:create, /vault-x:list, /vault-x:view, /vault-x:research, /vault-x:grow
scripts/                # Python implementations (uses pyyaml)
  vault-init.py         # Scaffold federation root + CLAUDE.md
  vault-create.py       # Scaffold a new vault dir + overview.md + CLAUDE.md + .obsidian/
  vault-list.py         # Federation overview — recursive: any dir with overview.md, named by path
  vault-view.py         # Single-vault map (path resolution + folder-relative wiki-link graph)
  research-scaffold.py  # Deterministic: deep-research run JSON -> dated run in research/<slug>/
  research-source.py    # Deterministic: one raw source note -> research/<slug>/sources/ (used by grow)
workflows/              # Workflow scripts launched via Workflow({scriptPath})
  deep-research-local.js # Fork of Anthropic's deep-research — skips the flaky Scope agent (angles supplied)
templates/              # Files written by init/create/research
  federation-CLAUDE.md
  vault-CLAUDE.md
  vault-overview.md
  research-topic-overview.md   # research topic-vault identity (written on first run into a topic)
  research-topic-CLAUDE.md     # research topic-vault run-folder conventions
```

## Vault identity (path-based)

A vault is **any directory containing `overview.md`**, named by its path relative to the
federation root. This covers both flat curated vaults (`goddard-vault`) and namespaced
research vaults (`research/local-llms`). `vault-list` discovers them recursively;
`vault-view <name>` resolves by relative path, then legacy `<name>-vault`, then a unique
leaf match. Run folders have no `overview.md`, so they are never treated as vaults.

## The `research` command (deep-research integration)

`/vault-x:research "<question>"` turns a one-shot research report into persistent,
wiki-linked vault knowledge. It runs **only in the main loop** and sequences three tools:

1. **Deep-research (local fork)** — `workflows/deep-research-local.js`, run via
   `Workflow({scriptPath, args:{question, angles}})`. A fork of Anthropic's bundled deep-research
   (fan-out search → adversarial verify → cited synthesis) that **skips the native Scope agent**:
   that agent aborts runs by mis-emitting structured output (JSON↔XML slip) and *throws*, killing
   the whole run at its single non-redundant root step. Instead the command generates the 5 search
   angles in the main loop (reliable) and passes them in. Agents are pinned to `opus`. Returns the
   same structured JSON `{question, summary, findings[], caveats, openQuestions[], sources[], stats}`,
   so downstream is unchanged. **It's a pinned snapshot — re-sync if Anthropic updates deep-research.**
2. **`web-x` enrichment** — the native Fetch phase uses shallow `WebFetch`, so video/JS/paywalled
   sources return `claimCount == 0`. The command deep-reads exactly those URLs via the `web-x:web`
   skill and passes them as an enrichment map.
3. **`research-scaffold.py`** — deterministically writes the run into `research/<slug>/` (no LLM in
   the writing step).

**Routing (always-confirm).** Before running the harness, the command reads existing
`research/*/overview.md`, recommends a target (an existing topic vault or a new clean slug), and
**always** confirms via `AskUserQuestion` (recommendation pre-selected) — a run is too expensive to
silent-route. All research lives under the `research/` namespace, one topic vault per subject, each
accumulating dated runs. Two slugs: the **topic** names the vault (`--vault-slug local-llms`); the
**query** names the dated run folder (`--title` → `YYYY-MM-DD-<title-slug>/`).

`Workflow` is a **main-loop-only tool** — the command must never be delegated to a subagent.
Each run folder holds `report.md`, `blueprint.md`, `sources.md`, and `raw/`.

## The `grow` command (vault maturation)

`/vault-x:grow <vault>` matures an existing research topic vault in two connected phases:
**breadth** then **depth**. It runs in the main loop and composes the pieces above:

1. **Assess** — read the vault's runs and summarize coverage + gaps.
2. **Breadth** — propose gap questions, confirm via `AskUserQuestion`, and run
   `/vault-x:research`'s flow (routing-free — vault is known) for each pick.
3. **Depth** — rank sources across **all** runs by cross-run citation × quality, pull the
   top ~8 full-texts via `web-x:web`, and write them via `research-source.py` into a
   **vault-level `sources/` library** (deduped, each stamped `published`/`retrieved`/`cited_by`).

Depth *after* breadth is deliberate: it lets sources be ranked across the whole matured
vault. A topic vault thus becomes two layers — **runs** (analysis) + **`sources/`** (raw
evidence). A single `/vault-x:research` only self-heals its own failed fetches; all
deliberate depth lives in `grow`.

## Prerequisites

- Python 3.9+
- `pyyaml` — for frontmatter parsing. Install: `pip install pyyaml` or `uv pip install pyyaml`.

## Federation root

Default: `~/knowledge-vaults/`. Override with `--root <path>` on any command.

## Substrate the tools rely on

Every file in a managed vault carries YAML frontmatter (schema declared per-vault in its `CLAUDE.md`). Files reference each other via `[[wiki-links]]`, hermetic per vault. The tool layer walks the filesystem on demand — nothing is pre-indexed.

## Testing

```bash
python3 scripts/vault-init.py --root /tmp/test-kv
python3 scripts/vault-create.py my-vault --root /tmp/test-kv --purpose "A test vault."
python3 scripts/vault-list.py --root /tmp/test-kv
python3 scripts/vault-view.py my-vault --root /tmp/test-kv
```

Test the research scaffolder without spending research tokens — feed it a canned
deep-research run JSON (and optional enrichment map), then inspect the topic vault:

```bash
python3 scripts/research-scaffold.py --input run.json --vault-slug local-llms \
  --vault-title "Local LLMs" --vault-purpose "Local LLM research." \
  --title "Best local-LLM machine 2026" --root /tmp/test-kv --enriched enriched.json
python3 scripts/vault-list.py --root /tmp/test-kv                     # research/local-llms appears
python3 scripts/vault-view.py research/local-llms --root /tmp/test-kv # runs + link graph
```

## Architecture decisions

See `../docs/vault-plugin-planning.md` for design rationale and the decisions log.
