#!/usr/bin/env python3
"""Extract clean markdown from a web page. Tries trafilatura first, escalates to crawl4ai.

Usage: python3 web-fetch.py <url> [--js]

--js flag skips trafilatura and goes straight to crawl4ai (headless Chromium).
Without --js, tries trafilatura first. If result is thin (<200 chars), auto-escalates.
"""
from __future__ import annotations

import shutil
import subprocess
import sys


def check_trafilatura() -> bool:
    return shutil.which("trafilatura") is not None


def check_crawl4ai() -> bool:
    return shutil.which("crwl") is not None


def run_trafilatura(url: str) -> str:
    result = subprocess.run(
        ["trafilatura", "-u", url, "--formatting", "--links", "--images"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def run_crawl4ai(url: str) -> str:
    result = subprocess.run(
        ["crwl", "crawl", url, "-o", "markdown"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"Error: crawl4ai failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    return result.stdout.strip()


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 web-fetch.py <url> [--js]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    use_js = "--js" in sys.argv[2:]

    if use_js:
        if not check_crawl4ai():
            print("Error: crawl4ai not found. Install with: uv tool install crawl4ai && crawl4ai-setup", file=sys.stderr)
            sys.exit(1)
        output = run_crawl4ai(url)
        print(output)
        return

    # Try trafilatura first
    if not check_trafilatura():
        # Fall through to crawl4ai if available
        if check_crawl4ai():
            print("trafilatura not found, using crawl4ai instead.", file=sys.stderr)
            output = run_crawl4ai(url)
            print(output)
            return
        print("Error: trafilatura not found. Install with: uv tool install trafilatura", file=sys.stderr)
        sys.exit(1)

    output = run_trafilatura(url)

    if len(output) < 200:
        # Thin result — escalate to crawl4ai
        if check_crawl4ai():
            print("Trafilatura returned thin content, escalating to crawl4ai (JS rendering).", file=sys.stderr)
            output = run_crawl4ai(url)
        elif not output:
            print("Error: trafilatura returned empty result. Install crawl4ai for JS rendering: uv tool install crawl4ai && crawl4ai-setup", file=sys.stderr)
            sys.exit(2)

    print(output)


if __name__ == "__main__":
    main()
