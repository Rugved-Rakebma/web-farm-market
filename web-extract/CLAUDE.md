# Web Extract — Development Guide

## Architecture

Unified web content extraction plugin with three backends. Python scripts in `scripts/` orchestrate the CLI tools. Commands reference scripts via `${CLAUDE_PLUGIN_ROOT}/scripts/`.

Two layers:

1. **Commands** (`/web-x:*`) — User-invocable workflows in `commands/`. Plugin name `"web-x"` creates the `/web-x:` prefix.
2. **Skills** — In `skills/web/SKILL.md`. Decision tree teaching Claude when to use each backend.

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
```

## Scripts

All scripts use Python 3.9+ stdlib only (no pip dependencies). They call CLI tools via subprocess.

| Script | Backend(s) | What It Orchestrates |
|--------|-----------|---------------------|
| `web-fetch.py` | trafilatura, crawl4ai | Try trafilatura → auto-escalate to crawl4ai if thin result |
| `web-transcript.py` | yt-dlp | Metadata extraction + subtitle download (auto → manual fallback) + VTT-to-plaintext |
| `web-crawl.py` | crawl4ai | BFS deep crawl with page cap validation |

## Backends (prerequisites)

| Tool | Install | Purpose |
|------|---------|---------|
| `trafilatura` | `uv tool install trafilatura` | Static page → markdown |
| `yt-dlp` | `uv tool install yt-dlp` | Video transcript + metadata |
| `crawl4ai` | `uv tool install crawl4ai && crawl4ai-setup` | JS-rendered pages + deep crawl |

All three are installed as standalone CLI tools via `uv tool install`. They are prerequisites — the plugin's scripts call them via subprocess.

## Testing

```bash
# From the plugin root
python3 scripts/web-fetch.py "https://paulgraham.com/greatwork.html"
python3 scripts/web-transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
python3 scripts/web-crawl.py "https://docs.example.com" 5
```
