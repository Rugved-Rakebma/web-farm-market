---
description: Deep crawl a website and extract content from multiple pages
argument-hint: <url> [max_pages]
---

## Process

Crawl site: **$ARGUMENTS**

1. **Parse arguments.** Extract URL and optional max_pages from `$ARGUMENTS`. Default: 10 pages. Cap at 50 if user requests more.

2. **Run the crawl:**
   ```bash
   just web-crawl "<url>" <max_pages>
   ```

3. **Present results** to the user:
   - Number of pages crawled
   - List of pages with titles (as a table or bullet list)
   - Summary of total content extracted
   - Note the output location if files were written to disk

4. **Handle errors:**
   - Timeout on large sites → report partial results, suggest reducing max_pages
   - Permission denied / robots.txt → report which pages were blocked
   - Network errors → report and suggest retrying

## Notes

- Uses crawl4ai (headless Chromium) with BFS strategy — handles both static and JS-rendered sites.
- For single page extraction, suggest `/web-x:fetch` instead.
- Large crawls (20+ pages) can take minutes and produce significant output.
