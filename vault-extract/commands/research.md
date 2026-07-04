---
description: Run deep research and archive it as a dated run in a research topic vault
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

2. **Discover existing research vaults.** Read `<root>/research/*/overview.md`
   (default root `~/knowledge-vaults/`) for each topic vault's `name`, `purpose`,
   and `topics`. If `research/` doesn't exist yet, there are none.

3. **Decide a recommended target.** Judge whether this question clearly belongs to
   an existing research topic vault (strong topic match) or is a new topic. If new,
   invent a **short, clean topic slug** (e.g. `local-llms`, `pi-agent` — lowercase,
   kebab-case, no `-vault` suffix) plus a one-line purpose and a display title.
   Default granularity is **broad** — prefer folding a related query into an
   existing vault over spawning a near-duplicate.

4. **Always confirm the target — never silent-route.** A run costs ~2M tokens and
   ~10 minutes, so confirm *before* running. Ask with `AskUserQuestion`
   (header "Target vault"): option 1 = your recommendation, labelled "(Recommended)"
   (either "Add to `research/<slug>`" or "Create new: `research/<slug>`"); options
   2–3 = other plausible existing vaults and/or the create-new alternative. The
   user can pick "Other" to type a custom slug. Resolve the answer to a final
   `<vault-slug>` (+ a display title and one-line purpose if it's new).

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

10. **Scaffold into the chosen topic vault.** Pass the `--vault-slug` from step 4,
    a concise `--title` (~6–10 word label), and — for a new vault — `--vault-title`
    and `--vault-purpose`:
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/scripts/research-scaffold.py \
      --input <run.json> --vault-slug "<slug>" --title "<short label>" \
      [--vault-title "<Topic>"] [--vault-purpose "<one line>"] \
      [--enriched <enriched.json>] [--root <path>]
    ```
    Omit `--enriched` if step 8 produced nothing. `--vault-title`/`--vault-purpose`
    are only used when the topic vault is created for the first time.

11. **Report** the run-folder path the script prints, and suggest
    `/vault-x:view research/<slug>` to see it on the vault map.

## Notes

- All research lands under the `research/` namespace, **one topic vault per subject**
  (`~/knowledge-vaults/research/<slug>/`) — each a standard federation member visible
  in `/vault-x:list`. Topic vaults are created on first use and accumulate dated runs.
- Each run is a dated folder `YYYY-MM-DD-<title-slug>/` with `report.md`,
  `blueprint.md`, `sources.md`, and `raw/` (only when web-x enriched something).
- This is a **lab notebook**. Promotion of findings into curated topic vaults is manual.
- For throwaway research you don't want archived, call `deep-research` directly.
