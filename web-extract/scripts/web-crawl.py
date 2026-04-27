#!/usr/bin/env python3
"""Deep crawl a website and extract content from multiple pages via crawl4ai.

Usage: python3 web-crawl.py <url> [max_pages]

Default: 10 pages. Capped at 50.
"""
from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 web-crawl.py <url> [max_pages]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    max_pages = 10

    if len(sys.argv) >= 3:
        try:
            max_pages = int(sys.argv[2])
        except ValueError:
            print(f"Error: max_pages must be a number, got: {sys.argv[2]}", file=sys.stderr)
            sys.exit(1)

    max_pages = min(max(max_pages, 1), 50)

    if shutil.which("crwl") is None:
        print("Error: crawl4ai not found. Install with: uv tool install crawl4ai && crawl4ai-setup", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run(
        ["crwl", "crawl", url, "-o", "markdown",
         "--deep-crawl", "bfs", "--max-pages", str(max_pages)],
        capture_output=True, text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.returncode != 0:
        print(f"Error: crawl4ai failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
