# How the Deep-Research Harness Ran 108 Agents

> Reconstructed from the actual run on 2026-07-02 (task `ww1t8fgnp`) — the native
> `deep-research` workflow that `/vault-x:research` calls. Numbers are exact, taken
> from the harness script (read out of the CLI binary) and the run's own stats.

## The one big idea

`deep-research` is a **JavaScript orchestration script** that spawns many short-lived
**subagents** — each a full, independent Claude instance with its own context. The
script holds all intermediate state (search results, claims, votes) in plain JS
variables **outside any LLM context window**. Only the final ~small JSON comes back
to the main loop.

That's why "108 agents / 2 million tokens" never touched my context here — I saw only
the returned report object. It's how the harness researches at a scale one context
can't hold.

## This run, by the numbers

| Metric | Value |
|---|---|
| Agents spawned | **108** |
| Subagent tokens | ~2,035,000 |
| Tool calls (WebSearch/WebFetch/StructuredOutput) | 454 |
| Wall-clock | ~9.9 minutes |
| Sources fetched | 26 |
| Claims extracted → verified → confirmed | 129 → 25 → 21 |

The 108 is not arbitrary. The script's own formula:

```
agents = 1 (scope) + angles + sources + (verifiedClaims × 3 votes) + 1 (synthesize)
       = 1 + 5 + 26 + (25 × 3) + 1
       = 108
```

## The five phases

```
                    ┌─────────────────────────────────────────────┐
   [1] SCOPE        │ 1 agent · decomposes the question into 5     │  sequential
       │            │ complementary search angles (structured out) │  (must finish first)
       ▼            └─────────────────────────────────────────────┘
   ┌───────────────────────── PIPELINE — no barrier ─────────────────────────┐
   │ [2] SEARCH            [3] FETCH + EXTRACT                                 │
   │  5 agents             26 agents                                          │
   │  one per angle        one per deduped source URL                         │
   │  WebSearch →          WebFetch → up to 5 falsifiable claims + a quote     │
   │  top 4–6 URLs         + a source-quality rating                          │
   │                                                                          │
   │  As EACH angle's search returns, its novel URLs immediately fan out to   │
   │  fetch agents — angle B is still searching while angle A is fetching.    │
   │  Inline between them: URL-dedup (2 dupes dropped) + a fetch budget       │
   │  (2 low-relevance URLs dropped).                                         │
   └──────────────────────────────────────────────────────────────────────────┘
       │
       ▼   ◄── BARRIER: all fetches must finish, then the full claim pool is
   [rank + cap]   ranked (importance, then source quality) and capped at 25.
       │          129 claims → top 25 go to verification.
       ▼
   ┌───────────── PARALLEL (nested) — the bulk of the run ───────────────┐
   │ [4] VERIFY   25 claims × 3 skeptical voters = 75 agents               │
   │              Each voter is told to REFUTE (WebSearch for              │
   │              contradictions, default to "refuted" if unsure).         │
   │              A claim SURVIVES only if <2 of 3 votes refute it.        │
   │              → 21 confirmed, 4 killed                                  │
   └───────────────────────────────────────────────────────────────────────┘
       │
       ▼
   [5] SYNTHESIZE   1 agent · merges duplicate claims, groups into findings,
                    writes summary + caveats + open questions (structured out).
```

## How the parallelism actually works

Three different concurrency shapes, chosen per stage:

- **Pipeline (Search → Fetch):** no barrier between the two stages. Each source flows
  through search→fetch on its own; a fast angle's sources are already being read while
  a slow angle is still searching. Wall-clock ≈ the slowest single chain, not the sum.
- **Barrier before Verify:** intentional. You can't rank-and-cap the top 25 claims until
  every fetch has reported, so the script waits for the whole pool here.
- **Nested parallel (Verify):** 25 claims fan out, and *within* each claim its 3 votes
  fan out too — 75 independent agents.

None of these run all-at-once. A global cap of **min(16, CPU cores − 2)** concurrent
agents means the 108 run in waves, queuing as slots free up. The 75-agent verify phase
is what dominates the ~10-minute wall-clock.

## Key mechanisms worth knowing

- **Structured output everywhere.** Every agent is forced to return JSON against a schema
  (scope / search / extract / verdict / report). This is also the harness's fragile point:
  if an agent can't produce valid structured output after 5 retries, its phase dies — which
  is exactly what killed attempt 1 (the Scope agent) and degraded the Synthesize step on the
  run that completed.
- **Adversarial, recall-tuned verification.** Voters try to *refute*; a claim needs 2 of 3
  refutations to die. This kills plausible-but-wrong claims while letting well-supported ones
  through (4 of 25 were killed here — e.g. "Spark ≈ Strix Halo parity" marketing claims).
- **Budgets keep it bounded.** `MAX_FETCH` (fetch slots, high-relevance URLs bypass it),
  `MAX_VERIFY_CLAIMS = 25` (cap the pool), `VOTES_PER_CLAIM = 3`. Without these, breadth
  would explode.

## Where our plugin plugs in

`/vault-x:research` sits *outside* this box. It calls the harness, waits for the returned
JSON, then does two things the harness doesn't: (1) deep-reads any source the shallow
`WebFetch` skimmed (`claimCount == 0`) via `web-x`, and (2) writes the whole run —
report, blueprint, sources, raw — into the target vault (a tier-2 `research/<slug>/` by
default, or a tier-1 `<name>-vault/`) as a permanent, wiki-linked
record. The harness produces a throwaway report; we make it compound.

*(On this run the native Synthesize step returned placeholder text, so the orchestrator
re-synthesized the report from the 21 verified claims — see the pending fix in
`vault-plugin-planning.md`.)*
