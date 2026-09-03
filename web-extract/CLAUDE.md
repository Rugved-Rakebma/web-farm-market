# Web Extract — Development Guide

## Architecture

Unified web content extraction plugin with four backends. Python scripts in `scripts/` orchestrate the CLI tools. Commands reference scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/`.

Two layers:

1. **Commands** (`/web-x:*`) — User-invocable workflows in `commands/`. Plugin name `"web-x"` creates the `/web-x:` prefix.
2. **Skills** — Two skills under `skills/`:
   - `web/SKILL.md` — routing decision tree teaching Claude when to use each backend.
   - `output/SKILL.md` — output format contract: standardized YAML frontmatter, filename slug rules, per-type body conventions for Obsidian-friendly `.md` files.

## Plugin Structure

```
commands/           # /web-x:fetch, /web-x:transcript, /web-x:crawl
scripts/            # Python orchestration (stdlib only)
  web-fetch.py      # 3-tier ladder: trafilatura → crawl4ai → scrapling stealthy-fetch
  web-transcript.py # yt-dlp metadata + subtitle download + VTT parsing
  web-crawl.py      # crawl4ai BFS deep crawl
skills/
  web/              # Routing decision tree + backend documentation
    SKILL.md
  output/           # File-shape contract for materializing extractions as .md
    SKILL.md
```

## Scripts

All scripts use Python 3.9+ stdlib only (no pip dependencies). They call CLI tools via subprocess.

| Script | Backend(s) | What It Orchestrates |
|--------|-----------|---------------------|
| `web-fetch.py` | trafilatura, crawl4ai, scrapling | 3-tier ladder driven by `classify()`; every tier's output gated through `emit()` |
| `web-transcript.py` | yt-dlp | Player-client fallback chain + metadata + caption download (auto → manual) + json3/VTT-to-plaintext |
| `web-crawl.py` | crawl4ai | BFS deep crawl with page cap validation |

## Backends (prerequisites)

| Tool | Install | Purpose |
|------|---------|---------|
| `trafilatura` | `uv tool install trafilatura` | Static page → markdown (fetch tier 1) |
| `crawl4ai` | `uv tool install crawl4ai && crawl4ai-setup` | JS render (fetch tier 2) + deep crawl |
| `scrapling` | `uv tool install "scrapling[fetchers,rag]" && scrapling install` | Anti-bot challenge solving (fetch tier 3) |
| `yt-dlp` | `uv tool install yt-dlp` | Video transcript + metadata |

All four are installed as standalone CLI tools via `uv tool install`. They are prerequisites — the plugin's scripts call them via subprocess.

**scrapling needs BOTH extras.** `fetchers` alone installs fine and then fails at runtime
with *"Markdown conversion requires the markdownify package"* — markdown output lives in the
`rag` extra. The CLI docs do not mention this. `scrapling install` then fetches the browsers.

**Keep yt-dlp current** — `uv tool upgrade yt-dlp`. YouTube changes extraction surfaces
often and yt-dlp warns when a build is >90 days old.

## The fetch ladder (why each tier is the tool it is)

| Tier | Backend | Cost | Fires when |
|---|---|---|---|
| 1 | trafilatura | <1s | default |
| 2 | crawl4ai (headless Chromium) | 3–5s | tier 1 returns `thin` — page needs JS |
| 3 | scrapling `stealthy-fetch --solve-cloudflare` | 9–30s | any tier returns `blocked` |

Each tier is the best tool for **its own job**, not a general-purpose fallback. Benchmarked
2026-09-03; do not "simplify" the ladder without re-running these:

- **trafilatura stays tier 1.** It is a boilerplate-removal specialist and beats the
  alternatives at it. Against `scrapling extract get --ai-targeted`: on
  `paulgraham.com/greatwork.html` trafilatura returns clean prose while scrapling converts
  the page's 1990s layout tables into ~8KB of markdown table scaffolding (67,566 vs 59,840
  bytes); on `simonwillison.net` scrapling leaks the masthead, the Subscribe link and a
  sponsor ad block that trafilatura drops. Folding tier 1 into scrapling makes output worse.
- **crawl4ai stays tier 2.** `web-crawl.py` already requires it, so it costs nothing extra,
  and it resolves relative links to absolute URLs where `scrapling extract fetch` leaves
  them relative — relative links are broken links once `vault-x` archives the page.
  Rendering quality is otherwise equivalent (verified on `quotes.toscrape.com/js`).
- **scrapling is tier 3 only.** It is the only backend here that can clear an anti-bot
  challenge: verified against `nopecha.com/demo/cloudflare`, solving an interactive Turnstile
  in 9.2s and returning 26KB of real content. Its weaker article extraction is irrelevant at
  this tier because the alternative at this tier is nothing at all.

`--js` starts at tier 2, `--stealth` jumps straight to tier 3.

**`emit()` is terminal by design** — it exits rather than returns. An earlier revision let it
fall through, so after tier 3 printed a good page control resumed in the caller and
re-emitted the *blocked* tier-2 body: stdout got 26KB of correct content alongside exit 3.
Ending the process inside `emit()` makes that whole class of fall-through unreachable.

## Anti-bot challenge pages (why `web-fetch.py` classifies instead of measuring)

Anti-bot systems answer with **HTTP 200 and a fully-formed challenge page**. Cloudflare's
interstitial renders to ~500 chars of markdown — over any "is this thin?" threshold — so a
length check alone hands the challenge back to the caller as the article. Verified against
`nopecha.com/demo/cloudflare` before the fix: 495 bytes, **exit 0**, body reading
*"Performing security verification … Ray ID: a32e1c724b9cae18"*.

That is worse than an error. An error stops the caller; a silent wrong answer gets
summarised, cited, and archived into a vault as a source. `vault-x` consumes this script.

Same failure class as the YouTube section below — a block that does not look like a block.
Same remedy: **match content signatures, not lengths.**

`classify()` returns `ok` / `thin` / `blocked`. Blocked requires **both** a body under
`BLOCK_MAX_CHARS` (2000) **and** a `BLOCK_MARKERS` hit. The pairing is load-bearing: an
article *about* Cloudflare contains the word and would false-positive on signature alone,
but runs to thousands of characters. Verified: the Scrapling stealth-fetching docs page
mentions Cloudflare 26 times and classifies `ok` at 22,972 bytes.

Blocked exits **3**, distinct from extraction failure (2), and the body is **not** printed.
Never widen `BLOCK_MARKERS` with a string that could plausibly head a legitimate short page.

## Known gap: no prompt-injection sanitising

Emitted markdown is **not** stripped of CSS-hidden text, `aria-hidden` nodes or zero-width
unicode, any of which can carry instructions aimed at whatever model reads the result. This
plugin's entire job is piping untrusted web content into an agent's context, and `vault-x`
archives that content as cited sources — so the exposure is real, not theoretical.

Tier 3 gets this for free via scrapling's `--ai-targeted`, but tiers 1 and 2 do not, and a
pipeline is only as sanitised as its most-used path. Tier 1 serves the large majority of
fetches.

Deliberately **not** half-fixed. A partial strip is the worst outcome: it reads as a
mitigation while leaving vectors open. The real fix is one sanitising pass applied to
`emit()` so every tier is covered, and it needs care — naive zero-width stripping breaks ZWJ
emoji sequences and Persian/Arabic ZWNJ. Until then, treat every result as untrusted input.

## YouTube bot-gating (why `web-transcript.py` pins player clients)

yt-dlp's default YouTube clients are `('visionos', 'web')`. The `web` client scrapes the
`/watch` HTML page, which YouTube rate-limits per-IP. Once tripped, `/watch` 302-redirects
to `google.com/sorry/index` and returns **HTTP 429**; yt-dlp reports this as *"Sign in to
confirm you're not a bot"*, which wrongly suggests an auth problem. It is an endpoint
throttle, not an account issue — `google.com/search` and `youtube.com/` still return 200.

`web-transcript.py` walks `CLIENT_CHAIN = (android, visionos, android_vr, ios,
web_embedded, default)`. These reach the InnerTube player API and never touch `/watch`.
Verified matrix under an active throttle:

| Client | Metadata | Captions |
|---|---|---|
| android, visionos, android_vr, ios, web_embedded | ✅ | ✅ |
| web_safari, mweb | ✅ | ❌ |
| tv, tv_downgraded | ❌ | ❌ |
| web_music | ❌ | ❌ |

Captions come from the `timedtext` endpoint, which is **not** PO-token gated the way media
streams are — so transcripts keep working even when `--list-formats` fails.

**Never use `--cookies-from-browser`.** It needs the browser's master cookie-encryption key
(macOS keychain `Chrome Safe Storage`), which decrypts cookies for *every* site, not just
YouTube. yt-dlp's own FAQ separately warns that account cookies risk the account being
banned. The client chain needs no credentials.

Two other flags the script sets: `--js-runtimes` (yt-dlp only auto-detects `deno`; `node`
and `bun` must be named) and `--sleep-requests 1` (avoids re-tripping the throttle).

Captions are requested as `json3/vtt/best`. Prefer json3 — VTT auto-captions *roll*, so
consecutive segments repeat text and naive parsing duplicates whole sentences.

## Testing

```bash
# From the plugin root
python3 scripts/web-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python3 scripts/web-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --timestamps
python3 scripts/web-crawl.py "https://docs.example.com" 5
```

### The fetch ladder regression set

Four cases, one per path. Check the **exit code**, not just the output — the bug this whole
design exists to prevent produced correct-looking output with the wrong exit code.

```bash
# tier 1 only, no escalation          -> exit 0, ~59K
python3 scripts/web-fetch.py "https://paulgraham.com/greatwork.html"

# tier 1 thin -> tier 2 renders JS    -> exit 0, quotes present, links absolute
python3 scripts/web-fetch.py "https://quotes.toscrape.com/js/"

# tier 1 -> 2 -> 3, Turnstile solved  -> exit 0, ~26K of real page (NOT a challenge page)
python3 scripts/web-fetch.py "https://nopecha.com/demo/cloudflare"

# forced tier 3                       -> exit 0
python3 scripts/web-fetch.py "https://example.com" --stealth
```

**False-positive guard.** A page *about* anti-bot systems must classify `ok`, not `blocked`:

```bash
# mentions Cloudflare 26x -> exit 0, ~23K
python3 scripts/web-fetch.py "https://scrapling.readthedocs.io/en/latest/fetching/stealthy.html"
```

Quote the URL. An unquoted or double-quoted-inside-a-variable URL reaches the script with
literal quote characters, every tier fails on the malformed URL, and the run looks like a
backend outage rather than a harness bug.
