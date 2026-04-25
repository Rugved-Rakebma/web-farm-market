# Web Extract — Development Guide

## Architecture

Unified web content extraction plugin with three backends. No custom code — the plugin orchestrates existing CLI tools via `just` recipes.

Two layers:

1. **Commands** (`/web-x:*`) — User-invocable workflows in `commands/`. Plugin name `"web-x"` creates the `/web-x:` prefix.
2. **Skills** — In `skills/web/SKILL.md`. Decision tree teaching Claude when to use each backend.

## Plugin Structure

```
commands/           # /web-x:fetch, /web-x:transcript, /web-x:crawl
skills/
  web/              # Routing decision tree + backend documentation
    SKILL.md
```

## Backends (prerequisites)

| Tool | Install | Purpose |
|------|---------|---------|
| `trafilatura` | `uv tool install trafilatura` | Static page → markdown |
| `yt-dlp` | `uv tool install yt-dlp` | Video transcript + metadata |
| `crawl4ai` | `uv tool install crawl4ai && crawl4ai-setup` | JS-rendered pages + deep crawl |

All three are installed as standalone CLI tools via `uv tool install`. They are prerequisites — the plugin's `just` recipes call them directly.

## Just Recipes

| Recipe | Backend |
|--------|---------|
| `just web-fetch <url>` | trafilatura |
| `just web-fetch <url> --js` | crawl4ai |
| `just web-transcript <url>` | yt-dlp |
| `just web-crawl <url> [depth]` | crawl4ai |

Recipes are defined in `~/justfile` under the `[web]` group.
