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
├── Single web page?
│   ├── trafilatura (fast, no browser)
│   │   └── Result thin/empty? → escalate to crawl4ai (headless Chromium)
│   └── Result good → done
│
└── Multi-page site?
    └── crawl4ai → BFS crawl with max page limit
```

### Backends

| Backend | What It Does | Speed |
|---------|-------------|-------|
| **trafilatura** | Static HTML → clean markdown. Strips nav, ads, boilerplate. Extracts title, author, date, tags. | <1s per page |
| **yt-dlp** | Video platforms → transcript text + metadata (title, channel, duration, description). Thousands of supported sites. | 2-5s |
| **crawl4ai** | Headless Chromium renders JavaScript, then extracts. BFS multi-page crawl. Handles SPAs, dashboards, dynamic content. | 3-5s per page |

---

## Commands

| Command | Backend | What It Does |
|---------|---------|-------------|
| `/web-x:fetch <url>` | trafilatura → crawl4ai fallback | Single page to clean markdown |
| `/web-x:transcript <url>` | yt-dlp | Video transcript + metadata |
| `/web-x:crawl <url> [max_pages]` | crawl4ai (BFS) | Multi-page site extraction |

### Overlap with existing tools

| Tool | When to prefer it over web-x |
|------|------------------------------|
| **defuddle** | Quick article read already in conversation flow |
| **WebFetch** | URLs ending in `.md`, or when you want a model summary |
| **context7** MCP | Library/framework documentation specifically |

---

## Prerequisites

The plugin orchestrates three CLI tools. Install them before use:

```bash
uv tool install trafilatura
uv tool install yt-dlp
uv tool install crawl4ai
crawl4ai-setup
```

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
    ├── CLAUDE.md
    ├── commands/                     # 3 user-invocable commands
    │   ├── fetch.md                  # /web-x:fetch
    │   ├── transcript.md             # /web-x:transcript
    │   └── crawl.md                  # /web-x:crawl
    └── skills/
        └── web/
            └── SKILL.md              # Decision tree + backend documentation
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
