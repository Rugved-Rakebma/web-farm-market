---
description: Extract clean markdown content from a single web page
argument-hint: <url>
---

## Process

Extract content from: **$ARGUMENTS**

1. **Validate URL.** If `$ARGUMENTS` is empty or not a valid URL, ask the user for one.

2. **Check if this is a video URL.** If the URL matches a video platform (youtube.com, vimeo.com, tiktok.com, etc.), suggest `/web-x:transcript` instead and confirm with the user before proceeding.

3. **Run the fetch script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-fetch.py "$ARGUMENTS"
   ```
   The script tries trafilatura first (fast, no browser). If the result is thin (<200 chars), it auto-escalates to crawl4ai (headless Chromium). Use `--js` flag to skip straight to crawl4ai.

4. **Present the result** as clean markdown. Preserve all formatting, links, and structure.

## Notes

- For video URLs, suggest `/web-x:transcript` instead.
- For multi-page extraction, suggest `/web-x:crawl`.
- Alternative: the `defuddle` skill extracts articles via Node.js — lighter but requires npx.
