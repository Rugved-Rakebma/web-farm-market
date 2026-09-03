# Web Extract — Development Guide

## Architecture

Unified web content extraction plugin with three backends. Python scripts in `scripts/` orchestrate the CLI tools. Commands reference scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/`.

Two layers:

1. **Commands** (`/web-x:*`) — User-invocable workflows in `commands/`. Plugin name `"web-x"` creates the `/web-x:` prefix.
2. **Skills** — Two skills under `skills/`:
   - `web/SKILL.md` — routing decision tree teaching Claude when to use each backend.
   - `output/SKILL.md` — output format contract: standardized YAML frontmatter, filename slug rules, per-type body conventions for Obsidian-friendly `.md` files.

## Plugin Structure

```
commands/           # /web-x:fetch, /web-x:transcript, /web-x:crawl
scripts/            # Python orchestration (stdlib only)
  web-fetch.py      # trafilatura → crawl4ai fallback
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
| `web-fetch.py` | trafilatura, crawl4ai | Try trafilatura → auto-escalate to crawl4ai if thin or blocked; classify before emitting |
| `web-transcript.py` | yt-dlp | Player-client fallback chain + metadata + caption download (auto → manual) + json3/VTT-to-plaintext |
| `web-crawl.py` | crawl4ai | BFS deep crawl with page cap validation |

## Backends (prerequisites)

| Tool | Install | Purpose |
|------|---------|---------|
| `trafilatura` | `uv tool install trafilatura` | Static page → markdown |
| `yt-dlp` | `uv tool install yt-dlp` | Video transcript + metadata |
| `crawl4ai` | `uv tool install crawl4ai && crawl4ai-setup` | JS-rendered pages + deep crawl |

All three are installed as standalone CLI tools via `uv tool install`. They are prerequisites — the plugin's scripts call them via subprocess.

**Keep yt-dlp current** — `uv tool upgrade yt-dlp`. YouTube changes extraction surfaces
often and yt-dlp warns when a build is >90 days old.

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
python3 scripts/web-fetch.py "https://paulgraham.com/greatwork.html"
python3 scripts/web-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python3 scripts/web-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --timestamps
python3 scripts/web-crawl.py "https://docs.example.com" 5
```
