---
description: Run deep research and archive it as a dated run in a vault (either tier)
argument-hint: "<question>" [--root <path>]
---

## Process

Research question: **$ARGUMENTS**

This command orchestrates three tools. It **must run in the main loop** — the
`Workflow` tool is not available inside subagents, so do NOT delegate any step
below to a subagent.

1. **Parse args.** Extract the quoted `<question>` (required). Optional `--root`
   passes through to the scaffold script. If no question is given, ask for one.
   State the question clearly; an overly long question can be condensed to ~100
   words (preserving intent) — keep the user's full wording for your own reference.

2. **Discover the federation.** Run
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-list.py [--root <path>]` and read the
   result. It returns **every** vault at both tiers — tier-1 `<name>-vault/` and
   tier-2 `<classifier>/<slug>/` — with purpose, topics, domain, and updated date.
   Don't read `overview.md` files yourself; `vault-list` is the discovery surface.

3. **Decide a recommended target.** Three kinds of target exist:

   a. **An existing tier-2 vault** (`<classifier>/<slug>`) whose topic this question
      clearly extends. The default, and the default granularity is **broad** —
      prefer folding a related query into an existing vault over spawning a
      near-duplicate.
   b. **An existing tier-1 vault** (`<name>-vault`) — only when the question directly
      serves that vault's live subject. A run into a tier-1 vault is **additive**: it
      lands as one more dated run folder and never touches the hand-maintained
      layers, which outrank it. Read that vault's `CLAUDE.md` before recommending it.
   c. **A new tier-2 vault** — invent a **short, clean topic slug** (e.g. `local-llms`,
      `pi-agent` — lowercase, kebab-case, **no `-vault` suffix**: the classifier
      already names the kind) plus a one-line purpose and a display title.

   **`research` never creates a tier-1 vault.** New always means tier 2. Tier 1 is
   reached by `/vault-x:create` or `/vault-x:graduate`, never as a side effect of a
   research run — the scaffolder refuses it (exit 5).

4. **Always confirm the target — never silent-route.** A run costs ~2M tokens and
   ~10 minutes, so confirm *before* running. Ask with `AskUserQuestion`
   (header "Target vault"). Build the options from step 3 — do not use a fixed list:
   - option 1 = your recommendation, labelled "(Recommended)". Label it with its
     **full reference** so the tier is legible at a glance: `Add to
     research/local-llms`, `Add to personal-tax-vault`, or
     `Create new: research/<slug>`.
   - options 2–3 = the other plausible targets, mixing tiers freely — the strongest
     other existing vault (either tier) and the create-new alternative.
   - "Other" lets the user type a custom reference.

   Resolve the answer to a final **vault reference** — plus a display title and
   one-line purpose if it is a new tier-2 vault.

5. **Run deep research (via the local fork).** The native `deep-research` harness
   aborts at its Scope agent (it mis-emits structured output and throws), so we
   supply the search angles ourselves and run the plugin's forked workflow, which
   skips that step:
   - **Decompose the question into 5 search angles** yourself — each `{label, query}`,
     covering complementary directions (broad/primary · technical/benchmarks ·
     recent · practitioner/implementation · contrarian/skeptical). Generating these
     in the main loop is reliable (the failure was the harness's Scope subagent).
   - Resolve the plugin root, then launch the fork and await its result JSON:
     ```bash
     echo ${CLAUDE_PLUGIN_ROOT}     # absolute plugin path for the scriptPath below
     ```
     ```
     Workflow({ scriptPath: "<plugin-root>/workflows/deep-research-local.js",
                args: { question: "<question>", angles: [ {label, query}, … 5 ] } })
     ```
   Return shape (use it directly — don't reformat):
   `{ question, summary, findings[], caveats, openQuestions[], refuted[],
   sources:[{url, quality, angle, claimCount}], stats }`.

6. **Check the synthesis — reconstruct if it degraded.** The native synthesize
   step is the run's fragile point: it sometimes returns placeholder output
   (e.g. `summary: "Test summary."`, a single finding despite many confirmed
   claims). Treat it as degraded if `findings` is empty, or its length is far
   below `stats.confirmed` (e.g. ≤1 finding when `stats.confirmed` ≥ 5), or
   `summary`/`caveats` read like placeholders. If degraded, **rebuild it yourself**:
   - The Workflow launch output printed a **transcript dir**. Find the synthesize
     agent's transcript: `grep -l "Confirmed claims" <transcript-dir>/agent-*.jsonl`.
   - Read the `## Confirmed claims` block from that agent's prompt — it lists every
     verified claim with its source, quote, and verifier evidence.
   - Synthesize a proper report: group claims into findings (each with `claim`,
     `confidence`, `sources[]`, `evidence`), and write `summary`, `caveats`,
     `openQuestions`. Note the reconstruction in `caveats`.
   - Replace `result.summary / findings / caveats / openQuestions`; keep `sources`,
     `refuted`, and `stats` intact.

7. **Select sources to deep-read.** Scan `result.sources[]` and collect every URL
   with `claimCount == 0` — sources the native `WebFetch` skimmed (video,
   JS-rendered, or paywalled). If none, skip to step 9.

8. **Enrich via web-x.** For each selected URL, use the **`web-x:web`** skill to
   extract full content. Build a `{ "<url>": "<raw markdown>" }` map and write it
   to a scratchpad temp file (e.g. `.../scratchpad/enriched.json`). Skip URLs
   web-x also fails on — don't block the run.

9. **Write the (possibly reconstructed) result JSON** to a scratchpad temp file
   (e.g. `.../scratchpad/run.json`).

10. **Scaffold into the chosen vault.** Pass the **vault reference** from step 4, a
    concise `--title` (~6–10 word label), and — for a new tier-2 vault —
    `--vault-title` and `--vault-purpose`:
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research-scaffold.py \
      --input <run.json> --vault "<ref>" --title "<short label>" \
      [--vault-title "<Topic>"] [--vault-purpose "<one line>"] \
      [--enriched <enriched.json>] [--root <path>]
    ```
    `--vault` accepts any reference: `research/local-llms`, `personal-tax-vault`, or a
    bare slug resolved federation-wide. Omit `--enriched` if step 8 produced nothing.
    `--vault-title`/`--vault-purpose` apply only when a new tier-2 vault is created.

    **Exit codes worth reading, not retrying blindly:**
    - `5` — a tier violation. Most often the reference is stale: the topic graduated
      and now lives at tier 1. The error names its new home; re-run with that.
    - `4` — a bare slug matched vaults at two tiers. Pass the full reference.
    - `3` — nothing resolved. Check `/vault-x:list`.

11. **Report** the run-folder path the script prints, and suggest
    `/vault-x:view <ref>` to see it on the vault map.

## Notes

- New research topics land under the `research/` classifier as **tier-2** vaults
  (`~/knowledge-vaults/research/<slug>/`), one topic per subject, created on first use
  and accumulating dated runs. A run may also target an existing **tier-1**
  `<name>-vault/`, where it lands as one more dated run alongside that vault's
  hand-maintained layers. Both tiers are visible in `/vault-x:list`.
- Each run is a dated folder `YYYY-MM-DD-<title-slug>/` with `report.md`,
  `blueprint.md`, `sources.md`, and `raw/` (only when web-x enriched something).
- A tier-2 vault is a **lab notebook**. When it acquires content a re-run couldn't
  reproduce — private records, a live decision document, a distilled position — the
  whole vault graduates to tier 1 via `/vault-x:graduate`. Nothing is copied out; the
  vault moves and its `CLAUDE.md` is rewritten. See `~/knowledge-vaults/CLAUDE.md`.
- For throwaway research you don't want archived, call `deep-research` directly.
