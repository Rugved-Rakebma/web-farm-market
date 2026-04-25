---
description: Extract clean markdown content from a single web page
argument-hint: <url>
---

## Process

Extract content from: **$ARGUMENTS**

1. **Validate URL.** If `$ARGUMENTS` is empty or not a valid URL, ask the user for one.

2. **Check if this is a video URL.** If the URL matches a video platform (youtube.com, vimeo.com, tiktok.com, etc.), suggest `/web-x:transcript` instead and confirm with the user before proceeding.

3. **Run trafilatura first** (fast, no browser):
   ```bash
   just web-fetch "$ARGUMENTS"
   ```

4. **Evaluate the result:**
   - If output is substantial (>200 chars of meaningful content), present the markdown to the user with any metadata (title, author, date) shown at the top.
   - If output is empty or very thin (<200 chars), the page likely requires JavaScript rendering.

5. **Escalate to crawl4ai if needed:**
   ```bash
   just web-fetch "$ARGUMENTS" --js
   ```
   Tell the user you're escalating because the page appears to require JavaScript rendering.

6. **Present the result** as clean markdown. Preserve all formatting, links, and structure.

## Notes

- For video URLs, suggest `/web-x:transcript` instead.
- For multi-page extraction, suggest `/web-x:crawl`.
- Alternative: the `defuddle` skill extracts articles via Node.js — lighter but requires npx.
