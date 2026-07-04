---
description: Mature a research topic vault — assess it, research the gaps, then deepen its top sources
argument-hint: <vault> (e.g. research/local-llms or local-llms)
---

## Process

Grow the vault: **$ARGUMENTS**

A vault-level maturation pass — it **broadens** the vault with gap-filling research,
then **deepens** it by pulling the most-important sources into a shared evidence
library. It runs **only in the main loop** (it invokes `Workflow`) and reuses
`/vault-x:research`'s machinery. Confirm at each checkpoint — the user can stop
after any phase.

1. **Resolve + assess.** Resolve the target to `research/<slug>` (accept a bare slug
   or full path; default root `~/knowledge-vaults/`). Read `overview.md` and each
   run's `report.md` (its `question` + top findings) plus each `sources.md`. Summarize:
   how many runs, what's **covered**, what's **thin or absent**, and any recurring
   **open questions**. Show this assessment. If the vault has no runs yet, say so and
   propose seed questions instead.

2. **Propose breadth — then confirm.** From the gaps and prior open questions, draft
   3–5 candidate research questions (tight, plain-ASCII, per `research` step 1). Ask
   with `AskUserQuestion` (multiSelect, strongest gaps first, header "Grow"). **State
   plainly that each selected question is a full ~2M-token / ~10-minute research run.**
   The user picks a subset — possibly **none** (then skip to step 4 for enrich-only).

3. **Research each selected gap.** For each pick, run the research sub-flow **without
   the routing prompt** (the target vault is already known):
   - decompose the question into 5 `{label, query}` angles and launch the local fork
     (see `research` step 5): `Workflow({ scriptPath: "<plugin-root>/workflows/deep-research-local.js", args: { question, angles } })`
   - synthesis-degradation check + reconstruct if needed (see `research` step 6)
   - enrich `claimCount == 0` sources via `web-x:web`
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research-scaffold.py --input <run.json>
     --vault-slug "<slug>" --title "<short label>" [--enriched <map.json>] [--root <path>]`

   Each run lands as a new dated folder and bumps `overview.updated` automatically.

4. **Deepen — enrich the top sources.** Aggregate **every** run's `sources.md` in the
   vault by normalized URL (strip `www.`/trailing slash). For each unique source track:
   how many runs cite it, its best `quality`, and total `claims`. Rank by
   **(runs-citing desc, then quality primary>secondary>blog, then total claims)** and
   take the **top ~8**. Show the ranked shortlist and confirm the pull (cheap — a
   handful of `web-x` calls). For each:
   - `web-x:web` to extract the full text; note its `published` date if surfaced.
   - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research-source.py --vault-slug "<slug>"
     --url "<url>" --input <markdown-file> [--published <date>] --cited-by <n> [--root <path>]`
   - Skip any URL web-x can't extract — don't block the pass.

5. **Report.** Summarize: N new runs added, M sources deepened into
   `research/<slug>/sources/`. Suggest `/vault-x:view research/<slug>`.

## Notes

- Result is a two-layer vault: **runs** (dated analysis) + **`sources/`** (a deduped
  raw-evidence library, each note stamped with `published` / `retrieved` / `cited_by`).
- `grow` never creates a new vault — it matures an existing one. Use `/vault-x:research`
  to start a topic; `grow` to develop it.
- Enrich-only: run `grow` and pick no gap questions to just refresh/extend the
  `sources/` library over the existing runs.
- Depth is deliberate and lives here; a single `/vault-x:research` only self-heals its
  own failed fetches, it doesn't build the source library.
