# web-x — Web Content Extraction for Claude Code

Three backends, one interface. Static pages, video transcripts, JS-rendered sites.

```
/plugin marketplace add Rugved-Rakebma/web-farm-market
/plugin install web-extract@web-farm-market
```

---

## The Problem

Claude Code has several ways to fetch web content, but each has gaps:

| Tool | Limitation |
|------|-----------|
| **WebFetch** (built-in) | Summarizes via small model — you get a digest, not the raw content |
| **defuddle** (obsidian plugin) | Node-only, single pages, no video, no crawling |
| **youtube_transcript** MCP | Single platform, Docker dependency, currently disabled |

No single tool handles the full surface: static articles, JS-rendered SPAs, video transcripts, and multi-page crawls. You end up juggling tools and guessing which one works for a given URL.

This plugin routes automatically.

---

## Quick Start

```
/web-x:fetch https://paulgraham.com/greatwork.html    # article → clean markdown
/web-x:transcript https://youtube.com/watch?v=...      # video → transcript + metadata
/web-x:crawl https://docs.example.com                  # site → multi-page extraction
```

---

## How It Works

The plugin teaches Claude a decision tree. Given a URL, it picks the right backend:

```
URL provided
│
├── Video platform? (youtube, vimeo, twitter, tiktok, twitch, etc.)
│   └── yt-dlp → transcript + metadata
│
├── Single web page? → three-tier ladder, escalating on the *classified* result
│   ├── tier 1  trafilatura         → ok?      done
│   ├── tier 2  crawl4ai            → on THIN     (page needs JS)
│   └── tier 3  scrapling stealth   → on BLOCKED  (site refused us)
│
└── Multi-page site?
    └── crawl4ai → BFS crawl with max page limit
```

Escalation is driven by **what the result is**, not how long it is. Anti-bot systems answer
with HTTP 200 and a fully-formed challenge page, so a length check alone returns the
challenge as though it were the article — see *Blocked ≠ empty* below.

### Backends

Each tier is the best tool for its own job, not a general-purpose fallback.

| Backend | What It Does | Speed |
|---------|-------------|-------|
| **trafilatura** | Static HTML → clean markdown. Strips nav, ads, boilerplate. Best-in-class article extraction. | <1s per page |
| **crawl4ai** | Headless Chromium renders JavaScript, then extracts. Resolves links to absolute URLs. BFS multi-page crawl. | 3-5s per page |
| **scrapling** | Fingerprint-spoofing browser that *solves* Cloudflare Turnstile and general bot-gating. Tier 3 only. | 9-30s per page |
| **yt-dlp** | Video platforms → transcript text + metadata (title, channel, duration, description). Thousands of supported sites. | 2-5s |

### Blocked ≠ empty

`/web-x:fetch` exits **3** when a site serves a challenge page instead of content, and
refuses to print the challenge body. A blocked fetch is a *refusal*, not a thin page — and
silently returning a Cloudflare interstitial as an article is worse than failing, because
it gets summarised, cited, and archived as a source.

---

## Commands

| Command | Backend | What It Does |
|---------|---------|-------------|
| `/web-x:fetch <url> [--js] [--stealth]` | trafilatura → crawl4ai → scrapling | Single page to clean markdown |
| `/web-x:transcript <url> [--timestamps]` | yt-dlp | Video transcript + metadata |
| `/web-x:crawl <url> [max_pages]` | crawl4ai (BFS) | Multi-page site extraction |

### Overlap with existing tools

| Tool | When to prefer it over web-x |
|------|------------------------------|
| **defuddle** | Quick article read already in conversation flow |
| **WebFetch** | URLs ending in `.md`, or when you want a model summary |
| **context7** MCP | Library/framework documentation specifically |

---

## Prerequisites

The plugin orchestrates four CLI tools. Install them before use:

```bash
uv tool install trafilatura
uv tool install yt-dlp
uv tool install crawl4ai && crawl4ai-setup
uv tool install "scrapling[fetchers,rag]" && scrapling install
```

> **scrapling needs both extras.** `fetchers` alone installs cleanly and then fails at
> runtime with *"Markdown conversion requires the markdownify package"* — markdown output
> lives in the `rag` extra.

If a backend is missing, commands print the exact install command:

```
Error: trafilatura not found. Install with: uv tool install trafilatura
```

---

## Repository Structure

```
web-farm-market/
├── .claude-plugin/
│   └── marketplace.json              # Marketplace definition
└── web-extract/                      # Plugin: web-x
    ├── .claude-plugin/plugin.json
    ├── CLAUDE.md                     # Dev guide + the hard-won backend doctrine
    ├── commands/                     # 3 user-invocable commands
    │   ├── fetch.md                  # /web-x:fetch
    │   ├── transcript.md             # /web-x:transcript
    │   └── crawl.md                  # /web-x:crawl
    ├── scripts/                      # Python orchestration (stdlib only)
    │   ├── web-fetch.py              # 3-tier ladder + block classification
    │   ├── web-transcript.py         # yt-dlp client chain + json3/VTT parsing
    │   └── web-crawl.py              # crawl4ai BFS deep crawl
    └── skills/
        ├── web/SKILL.md              # Decision tree + backend documentation
        └── output/SKILL.md           # Obsidian-friendly .md file-shape contract
```

## Install

```
/plugin marketplace add Rugved-Rakebma/web-farm-market
/plugin install web-extract@web-farm-market
```

## Author

Rugved Ambekar

## License

MIT
