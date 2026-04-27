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
│       python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-transcript.py <url>
│
├── Single web page?
│   ├── Try trafilatura first (fast, no browser needed)
│   │   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-fetch.py <url>
│   ├── Result empty/thin? Script auto-escalates to crawl4ai
│   └── Force JS rendering?
│       python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-fetch.py <url> --js
│
└── Multi-page site / deep crawl needed?
    └── crawl4ai deep crawl
        python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-crawl.py <url> [max_pages]
```

## Backends

### trafilatura (static pages)

- **Speed**: Fast (<1s per page), no browser overhead
- **Extracts**: Article text, title, author, date, tags, categories, comments
- **Output**: Clean markdown with formatting preserved
- **Limitations**: Cannot render JavaScript — misses SPAs and dynamic content

### yt-dlp (video platforms)

- **Coverage**: Thousands of sites (YouTube, Vimeo, Twitter/X, TikTok, Twitch, Dailymotion, SoundCloud, and many more)
- **Extracts**: Transcript/subtitles (auto-generated + manual), title, author/channel, duration, description, view count, upload date
- **Output**: Metadata + plain text transcript
- **Limitations**: Requires subtitles to exist (auto-generated or manual). Cannot transcribe audio.

### crawl4ai (JS-rendered / deep crawl)

- **Engine**: Headless Chromium via Playwright
- **Renders**: JavaScript before extraction — handles SPAs, React, Angular, dynamic content
- **Deep crawl**: BFS multi-page crawl with configurable page limit
- **Speed**: Slower (~3-5s per page due to browser rendering)

## Overlap with existing tools

| Tool | When to prefer it |
|------|-------------------|
| **defuddle** (obsidian plugin) | Quick article read already in conversation flow, Node-based |
| **WebFetch** (built-in) | URLs ending in .md, or when you need a model-summarized version |
| **web-x:fetch** (this plugin) | Raw markdown needed, full metadata, or defuddle/WebFetch return thin content |
| **web-x:transcript** (this plugin) | Any video URL — replaces disabled youtube_transcript MCP |
| **web-x:crawl** (this plugin) | Multi-page extraction, site-wide content gathering |

## Error handling

If a backend CLI is not installed, scripts print a clear error with the install command to stderr:

```
Error: trafilatura not found. Install with: uv tool install trafilatura
Error: yt-dlp not found. Install with: uv tool install yt-dlp
Error: crawl4ai not found. Install with: uv tool install crawl4ai && crawl4ai-setup
```
