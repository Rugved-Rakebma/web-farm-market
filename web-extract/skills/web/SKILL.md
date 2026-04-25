---
name: web-extract
description: Extract content from web pages, video platforms, and multi-page sites. Routes to the right backend automatically — trafilatura for static pages, yt-dlp for video transcripts, crawl4ai for JS-rendered or deep crawls. Use when the user provides a URL to extract content from, wants a video transcript, or needs to crawl a site. Do NOT use for URLs ending in .md (use WebFetch). For simple article reads, the defuddle skill is a lighter alternative.
---

# Web Extract

Unified web content extraction with three backends. Choose based on the source.

## Decision Tree

```
URL provided
├── Video platform? (youtube.com, youtu.be, vimeo.com, twitter.com/*/video,
│   tiktok.com, twitch.tv, soundcloud.com, dailymotion.com, etc.)
│   └── yt-dlp → transcript + metadata
│       Recipe: just web-transcript <url>
│
├── Single web page?
│   ├── Try trafilatura first (fast, no browser needed)
│   │   Recipe: just web-fetch <url>
│   ├── Result empty/thin? Likely JS-rendered (SPA, React, Angular, dashboard)
│   │   └── Escalate to crawl4ai
│   │       Recipe: just web-fetch <url> --js
│   └── Result good? → done
│
└── Multi-page site / deep crawl needed?
    └── crawl4ai deep crawl
        Recipe: just web-crawl <url> [depth]
```

## Backends

### trafilatura (static pages)

- **Speed**: Fast (<1s per page), no browser overhead
- **Extracts**: Article text, title, author, date, tags, categories, comments
- **Output**: Clean markdown with formatting preserved
- **Limitations**: Cannot render JavaScript — misses SPAs and dynamic content
- **Recipe**: `just web-fetch <url>`

### yt-dlp (video platforms)

- **Coverage**: Thousands of sites (YouTube, Vimeo, Twitter/X, TikTok, Twitch, Dailymotion, SoundCloud, and many more)
- **Extracts**: Transcript/subtitles (auto-generated + manual), title, author/channel, duration, description, view count, upload date
- **Output**: Metadata JSON + plain text transcript
- **Limitations**: Requires subtitles to exist (auto-generated or manual). Cannot transcribe audio.
- **Recipe**: `just web-transcript <url>`

### crawl4ai (JS-rendered / deep crawl)

- **Engine**: Headless Chromium via Playwright (already installed on this system)
- **Renders**: JavaScript before extraction — handles SPAs, React, Angular, dynamic content
- **Deep crawl**: BFS multi-page crawl with configurable depth
- **Speed**: Slower (~3-5s per page due to browser rendering)
- **Recipe**: `just web-fetch <url> --js` (single page) or `just web-crawl <url> [depth]` (multi-page)

## Overlap with existing tools

| Tool | When to prefer it |
|------|-------------------|
| **defuddle** (obsidian plugin) | Quick article read already in conversation flow, Node-based |
| **WebFetch** (built-in) | URLs ending in .md, or when you need a model-summarized version |
| **web-x:fetch** (this plugin) | Raw markdown needed, full metadata, or defuddle/WebFetch return thin content |
| **web-x:transcript** (this plugin) | Any video URL — replaces disabled youtube_transcript MCP |
| **web-x:crawl** (this plugin) | Multi-page extraction, site-wide content gathering |

## Error handling

If a backend is not installed, recipes print a clear error with the install command:

```
Error: trafilatura not found. Install with: uv tool install trafilatura
Error: yt-dlp not found. Install with: uv tool install yt-dlp
Error: crawl4ai not found. Install with: uv tool install crawl4ai && crawl4ai-setup
```
