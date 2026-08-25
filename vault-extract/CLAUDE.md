# Vault Extract — Development Guide

## Architecture

Manages a federation of structured knowledge-base vaults at `~/knowledge-vaults/`. Plugin slug `"vault-x"` creates the `/vault-x:` prefix.

Two parts:

1. **Commands** (`/vault-x:*`) — User-invocable workflows in `commands/`. Most call a Python script via `${CLAUDE_PLUGIN_ROOT}/scripts/`; `research` instead orchestrates other tools in the main loop (see below).
2. **Scripts** — Python orchestration in `scripts/`. Read template files from `templates/` at scaffold time.

## Plugin Structure

```
commands/               # /vault-x:init, :create, :list, :view, :research, :grow, :graduate
scripts/                # Python implementations (uses pyyaml)
  _common.py            # SHARED: tier-aware resolution, target paths, discovery, validation,
                        #   frontmatter, errors, the uniform entrypoint. Raises, never exits.
  vault-init.py         # Scaffold federation root + CLAUDE.md
  vault-create.py       # Scaffold a new TIER-1 vault + overview.md + CLAUDE.md + .obsidian/
  vault-list.py         # Federation overview — bounded two-level scan, grouped by tier
  vault-view.py         # Single-vault map (ref resolution + folder-relative wiki-link graph)
  vault-graduate.py     # Deterministic: tier-2 -> tier-1 move + overview/CLAUDE rewrite
  research-scaffold.py  # Deterministic: run JSON -> dated run in the target vault (either tier)
  research-source.py    # Deterministic: one raw source note -> <vault>/sources/ (used by grow)
workflows/              # Workflow scripts launched via Workflow({scriptPath})
  deep-research-local.js # Fork of Anthropic's deep-research — skips the flaky Scope agent (angles supplied)
templates/              # Files written by init/create/research/graduate
  federation-CLAUDE.md         # federation root — declares the two-tier standard
  vault-CLAUDE.md              # tier-1, created empty by `create`
  vault-overview.md            # tier-1 identity
  graduated-vault-CLAUDE.md    # tier-1, produced by `graduate` from a tier-2 vault
  research-topic-overview.md   # tier-2 identity (research/ classifier)
  research-topic-CLAUDE.md     # tier-2 conventions (research/ classifier)
```

## The two-tier standard

`templates/federation-CLAUDE.md` is canonical; this is the operational summary.

- **Tier 1** — `<name>-vault/` at the federation root. Graduated, hand-maintained, not
  reproducible by any classifier's tooling.
- **Tier 2** — `<classifier>/<slug>/`. Machine-produced; the classifier's tooling owns
  everything inside. The slug carries **no** `-vault` suffix.
- A `-vault` suffix means tier 1. Membership in a classifier means tier 2. **Never both.**
- `research/` is the only classifier. `--classifier` defaults to it; a classifier that
  doesn't exist yet requires `--allow-new-classifier`, so a typo can't spawn a permanent
  second tree.

A vault is a directory containing `overview.md` **at exactly one of those two positions**.
An `overview.md` deeper than that is vault content, not a vault. Discovery is a bounded
two-level `iterdir()` — never `rglob` — so tier and classifier are read off the position
rather than guessed, and a tier-1 vault is never descended into.

All resolution goes through `_common.resolve()`. A bare slug is resolved
**federation-wide with no tier preference**: matching vaults at two tiers is an error
(exit 4), not a silent pick. `vault-view`'s old local `resolve_vault()` is retired.

**Exit codes:** `1` general · `2` argparse usage · `3` not found · `4` ambiguous ·
`5` tier violation.

## Glossary

Three words, three meanings, no overlap.

| Term | Means |
|---|---|
| **Tiers** | The federation's two levels — tier 1 and tier 2. |
| **Layers** | The hand-maintained additions a tier-1 vault earned (records, live decision documents, distilled positions). |
| **Tracks** | Runs vs `sources/` *inside* one vault — both tool-owned. |

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
3. **`research-scaffold.py`** — deterministically writes the run into the target vault, tier-2
   `<classifier>/<slug>/` or tier-1 `<name>-vault/` (no LLM in the writing step).

**Routing (always-confirm).** Before running the harness, the command discovers the federation via
`vault-list.py` (**both tiers**), recommends a target, and **always** confirms via
`AskUserQuestion` (recommendation pre-selected) — a run is too expensive to silent-route. New
research topics land under the `research/` classifier, one topic vault per subject, each
accumulating dated runs; an existing tier-1 vault may also be targeted, where a run is purely
additive. **`research` never creates a tier-1 vault** — the scaffolder refuses it (exit 5). Two
slugs: the **topic** names the vault (`--vault research/local-llms`); the **query** names the dated
run folder (`--title` → `YYYY-MM-DD-<title-slug>/`).

**Anti-duplicate guard.** `resolve_write_target()` resolves federation-wide *before* deciding to
create. If the topic already exists at a different tier — the graduated case — it hard-errors
(exit 5) naming the real home instead of silently scaffolding a duplicate at the requested path.

`Workflow` is a **main-loop-only tool** — the command must never be delegated to a subagent.
Each run folder holds `report.md`, `blueprint.md`, `sources.md`, and `raw/`.

## The `grow` command (vault maturation)

`/vault-x:grow <vault>` matures an existing vault at **either tier** in two connected phases:
**breadth** then **depth**. It runs in the main loop and composes the pieces above:

1. **Assess** — read the vault's runs and summarize coverage + gaps.
2. **Breadth** — propose gap questions, confirm via `AskUserQuestion`, and run
   `/vault-x:research`'s flow (routing-free — vault is known) for each pick.
3. **Depth** — rank sources across **all** runs by cross-run citation × quality, pull the
   top ~8 full-texts via `web-x:web`, and write them via `research-source.py` into a
   **vault-level `sources/` library** (deduped, each stamped `published`/`retrieved`/`cited_by`).

Depth *after* breadth is deliberate: it lets sources be ranked across the whole matured
vault. A vault thus carries two tool-owned **tracks** — **runs** (analysis) +
**`sources/`** (raw evidence). In a tier-1 vault those tracks sit alongside the vault's
hand-maintained **layers**, which `grow` must never touch. A single `/vault-x:research`
only self-heals its own failed fetches; all deliberate depth lives in `grow`.

## The `graduate` command (tier promotion)

`/vault-x:graduate <classifier>/<slug>` moves a vault out from under its classifier's
tooling and makes it hand-maintained. **Script moves, Claude writes:**
`vault-graduate.py` validates, audits, rewrites `overview.md`'s frontmatter
(`name`/`domain`/`updated` + new `graduated`/`graduated_from`), drops
`graduated-vault-CLAUDE.md` in place with two marker blocks, and moves the directory.
Claude then fills the markers — only it knows what the vault earned.

**The audit is a necessary condition, not the graduation test.** It enumerates entries
the tooling could not have written (anything that isn't `overview.md`/`CLAUDE.md`/
`.obsidian/`/`sources/`/a dated run folder holding only the four known files). An empty
set is a refusal; a non-empty set is not an approval. Judgement stays in the command.

**Git.** The federation may be tracked by a **bare** repo with an external work-tree (the
`henv` pattern), so a plain `git mv` inside `~/knowledge-vaults` fails — there is no
`.git` in the ancestry. Resolution order: explicit `--git-dir`/`--work-tree` → env vars →
ordinary repo via `rev-parse --show-toplevel` → probe bare repos in `$HOME` and adopt the
one whose `ls-files` tracks the source path → fall back to `shutil.move` and print the
exact staging command. It never commits. The clean-tree gate passes `-uall`, because
`status.showUntrackedFiles=no` would otherwise read a dirty tree as clean.

Rewrites happen **in place, then the move** — so a failed move is one
`git checkout --` away. Re-running on an already-graduated vault exits 0.

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
python3 scripts/research-scaffold.py --input run.json --vault research/local-llms \
  --vault-title "Local LLMs" --vault-purpose "Local LLM research." \
  --title "Best local-LLM machine 2026" --root /tmp/test-kv --enriched enriched.json
python3 scripts/vault-list.py --root /tmp/test-kv                     # grouped by tier
python3 scripts/vault-view.py research/local-llms --root /tmp/test-kv # runs + link graph
```

Exercise the two-tier guards — each of these must FAIL with the stated code:

```bash
python3 scripts/research-scaffold.py --input run.json --vault research/local-llms-vault \
  --title t --root /tmp/test-kv                    # 5 — "never both"
python3 scripts/research-scaffold.py --input run.json --vault brand-new-vault \
  --title t --root /tmp/test-kv                    # 5 — never auto-creates tier 1
python3 scripts/vault-view.py research --root /tmp/test-kv          # 3 — classifier is not a vault
python3 scripts/vault-graduate.py research/local-llms --root /tmp/test-kv --dry-run
                                                   # 5 — nothing unreproducible yet
```

Then make it graduate-worthy and run the lifecycle:

```bash
mkdir /tmp/test-kv/research/local-llms/records
python3 scripts/vault-graduate.py research/local-llms --root /tmp/test-kv \
  --domain "local AI infrastructure"               # moves to local-llms-vault/
python3 scripts/vault-graduate.py local-llms-vault --root /tmp/test-kv   # 0 — already graduated
python3 scripts/research-scaffold.py --input run.json --vault research/local-llms \
  --title t --root /tmp/test-kv                    # 5 — stale ref, names the tier-1 home
```

## Architecture decisions

See `../docs/vault-plugin-planning.md` for design rationale and the decisions log.
