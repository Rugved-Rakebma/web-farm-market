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
  web-fetch.py      # 3-tier ladder: trafilatura → scrapling fetch → scrapling stealthy-fetch
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
| `web-fetch.py` | trafilatura, scrapling | 3-tier ladder driven by `classify()`; every tier sanitised by `prepare()` and gated through `emit()` |
| `web-transcript.py` | yt-dlp | Player-client fallback chain + metadata + caption download (auto → manual) + json3/VTT-to-plaintext |
| `web-crawl.py` | crawl4ai | BFS deep crawl with page cap validation |

## Backends (prerequisites)

| Tool | Install | Purpose |
|------|---------|---------|
| `trafilatura` | `uv tool install trafilatura` | Static page → markdown (fetch tier 1) |
| `crawl4ai` | `uv tool install crawl4ai && crawl4ai-setup` | Deep crawl only (`web-crawl.py`) |
| `scrapling` | `uv tool install "scrapling[fetchers,rag]" && scrapling install` | JS render (fetch tier 2) + anti-bot (fetch tier 3) |
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
| 2 | scrapling `extract fetch --ai-targeted` | 3–5s | tier 1 returns `thin` — page needs JS |
| 3 | scrapling `stealthy-fetch --solve-cloudflare --ai-targeted` | 9–30s | any tier returns `blocked` |

Each tier is the best tool for **its own job**, not a general-purpose fallback. Benchmarked
2026-09-03 / 2026-09-05; do not "simplify" the ladder without re-running these:

- **trafilatura stays tier 1.** It is a boilerplate-removal specialist and beats the
  alternatives at it. Against `scrapling extract get --ai-targeted`: on
  `paulgraham.com/greatwork.html` trafilatura returns clean prose while scrapling converts
  the page's 1990s layout tables into ~8KB of markdown table scaffolding (67,566 vs 59,840
  bytes); on `simonwillison.net` scrapling leaks the masthead, the Subscribe link and a
  sponsor ad block that trafilatura drops. Folding tier 1 into scrapling makes output worse.
- **crawl4ai was REMOVED from tier 2 in v1.4.0** on injection grounds — it leaked 9 of 9
  hidden-HTML vectors. See "Injection" below. It remains correct for `web-crawl.py`.
- **scrapling holds tiers 2 and 3.** Tier 3 is the only thing here that can clear an anti-bot
  challenge: verified against `nopecha.com/demo/cloudflare`, solving an interactive Turnstile
  in 9.2s and returning 26KB of real content. Its weaker article extraction is irrelevant at
  both tiers, because the alternatives are broken output or no output.
- **`--ai-targeted` is mandatory on tiers 2 and 3.** It is what strips hidden elements before
  markdown conversion. It is a security control, not a formatting preference.

`--js` starts at tier 2, `--stealth` jumps straight to tier 3.

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

## Injection: the measured backend comparison (why tier 2 changed in v1.4.0)

This plugin's whole job is piping attacker-controllable text into a model's context, and
`vault-x` archives that text as cited sources. Text a human cannot see but a model reads
verbatim is therefore the central threat, not a footnote.

`tests/fixture-injection.html` plants 12 vectors: hidden CSS, `aria-hidden`, `hidden` attr,
`<template>`, off-screen, white-on-white, `font-size:0`, HTML comment, zero-width runs,
Unicode tag chars, bidi override. Measured 2026-09-05:

| Backend | Hidden-HTML leaked | Invisible-unicode leaked |
|---|---|---|
| trafilatura | 2 of 9 | 0 |
| **crawl4ai** | **9 of 9** | 0 |
| scrapling `get --ai-targeted` | 0 of 9 | **4 chars** |
| scrapling `fetch --ai-targeted` | **0 of 9** | **0** |
| scrapling `stealthy-fetch --ai-targeted` | **0 of 9** | **0** |

crawl4ai leaked *every* hidden-HTML vector including `display:none` and `<template>`, and has
no CLI mitigation: `-o markdown-fit` is byte-identical, and `-c excluded_tags=...` fails
argument parsing and writes a **0-byte file that reads as a clean pass** — the same
empty-looks-like-success trap this plugin already guards against elsewhere. So tier 2 moved.

**trafilatura keeps tier 1 despite leaking 2 of 9.** Both leaks are computed-style
invisibility (`font-size:0`, white-on-white) that no markdown-level pass can detect, because
by the time text reaches `emit()` the style context is gone. It does strip `display:none`,
`visibility:hidden`, `aria-hidden`, `hidden`, `<template>`, off-screen and comments. Accepting
2 narrow vectors buys the <1s path that most fetches use.

### Reproduce

```bash
python3 -m http.server 8731 --directory tests &
python3 scripts/web-fetch.py "http://127.0.0.1:8731/fixture-injection.html" --js \
  | grep -o "CANARY_[A-Z]*" | sort -u      # must print nothing
python3 tests/scan-invisible.py <file>     # lists any invisible codepoints in a file
```

## `sanitize()` is a boundary guarantee, not a duplicate

No tier currently in the ladder leaks invisible Unicode — all three backends normalise it
away. `sanitize()` exists anyway because `scrapling extract get --ai-targeted` demonstrably
*does* leak it (4 chars above), proving the vector is live in the ecosystem rather than
theoretical. A backend swap must not be able to silently reopen it.

It runs **before `classify()`** for a second, independent reason: zero-width padding inside
`"Ray​ ID:"` evades block-signature matching entirely. Verified in `tests/test_sanitize.py` —
un-sanitised, that string matches no marker and classifies `thin`, so it would have been
returned as content.

Policy — strip only what has no legitimate role in prose:

| Stripped | Preserved |
|---|---|
| U+E0000–E007F tag chars · U+202A–202E, U+2066–2069 bidi · U+200B, U+2060, U+FEFF, U+180E, U+00AD | U+200C ZWNJ · U+200D ZWJ · U+FE00–FE0F variation selectors |

ZWJ/ZWNJ are orthographic in Arabic/Indic and structural in emoji sequences, so they survive
— **except between two ASCII characters**, where they can be neither. Both directions are
asserted in the tests; breaking that distinction silently corrupts real content.

Stripping is **reported to stderr**, never silent. Finding these characters is itself signal
that the page is hostile.

## Known gap: `web-x:crawl` still carries the crawl4ai leak

`web-crawl.py` still uses crawl4ai, which leaks 9 of 9 hidden-HTML vectors, and `/web-x:crawl`
archives many pages at once. **This is the top open gap in the plugin.**

It is not fixed here because scrapling has no CLI deep crawl — closing it means writing a real
`SiteToMarkdownSpider`, which is a different piece of work from a subprocess wrapper. Until
then, treat crawled output as materially less trustworthy than fetched output.

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
