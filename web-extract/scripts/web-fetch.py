#!/usr/bin/env python3
"""Extract clean markdown from a web page. Tries trafilatura first, escalates to crawl4ai.

Usage: python3 web-fetch.py <url> [--js]

--js skips trafilatura and goes straight to crawl4ai (headless Chromium).
Without it, trafilatura runs first and the result is classified (see below).

Exit codes: 0=success, 1=backend missing, 2=extraction failed, 3=blocked by anti-bot.

Why output is classified, not measured
--------------------------------------
Anti-bot systems answer with HTTP 200 and a fully-formed *challenge* page. Cloudflare's
interstitial renders to ~500 chars of markdown — comfortably over any "is this thin?"
threshold — so a length check alone hands the challenge page back to the caller as if it
were the article. Verified against nopecha.com/demo/cloudflare: 495 bytes, exit 0, content
reading "Performing security verification ... Ray ID: a32e1c724b9cae18".

That is worse than an error. An error stops the caller; a silent wrong answer gets
summarised, cited, and archived into a vault as though it were a source.

This is the same failure class web-transcript.py already handles for YouTube, where an
HTTP 429 arrives disguised as "Sign in to confirm you're not a bot" — a block that does
not look like a block. Same remedy here: match content signatures, not lengths.

classify() returns "ok", "thin", or "blocked". Blocked requires BOTH a short body AND a
challenge-page signature. The pairing is deliberate: an article *about* Cloudflare contains
the word "Cloudflare" and would false-positive on signature alone, but runs to thousands of
characters. A 500-char page that also says "Ray ID" is not an article about anything.
"""
from __future__ import annotations

import shutil
import subprocess
import sys

# Below this, a result carries no usable content regardless of what it says.
THIN_CHARS = 200

# Signature matching only applies below this length. Real articles that discuss anti-bot
# systems blow straight past it; challenge pages land far under it.
BLOCK_MAX_CHARS = 2000

# Lowercased substrings. Kept deliberately specific — a marker that could plausibly head a
# legitimate short page does not belong here, however common it is on block pages.
BLOCK_MARKERS = (
    # Cloudflare
    "just a moment",
    "checking your browser",
    "performing security verification",
    "enable javascript and cookies to continue",
    "needs to review the security of your connection",
    "ray id:",
    "cf-browser-verification",
    "attention required!",
    "sorry, you have been blocked",
    # Generic / multi-vendor
    "access denied",
    "you don't have permission to access",
    "request unsuccessful",
    "verify you are human",
    "are you a robot",
    "detected unusual activity",
    "unusual traffic from your computer network",
    "pardon our interruption",
    # DataDome / PerimeterX / Imperva
    "blocked by our security",
    "please enable js and disable any ad blocker",
    "incapsula incident id",
    "px-captcha",
)


def matched_marker(text: str) -> str | None:
    lowered = text.lower()
    for marker in BLOCK_MARKERS:
        if marker in lowered:
            return marker
    return None


def classify(text: str) -> str:
    """-> "ok" | "thin" | "blocked". See module docstring for why both tests are needed."""
    if len(text) < BLOCK_MAX_CHARS and matched_marker(text):
        return "blocked"
    if len(text) < THIN_CHARS:
        return "thin"
    return "ok"


def exit_blocked(text: str) -> None:
    marker = matched_marker(text) or "unknown"
    print(
        f'Error: blocked by an anti-bot challenge (matched: "{marker}").\n'
        "The site returned a challenge page, not content — this is a refusal, not an "
        "extraction failure, so the page body is deliberately NOT printed.\n"
        "Options: retry in a while, try a different network, or open the page manually.",
        file=sys.stderr,
    )
    sys.exit(3)


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


def emit(text: str) -> None:
    """Final gate. Nothing reaches stdout without being classified first."""
    if classify(text) == "blocked":
        exit_blocked(text)
    if not text:
        print("Error: extraction returned an empty result.", file=sys.stderr)
        sys.exit(2)
    print(text)


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
        emit(run_crawl4ai(url))
        return

    if not check_trafilatura():
        if check_crawl4ai():
            print("trafilatura not found, using crawl4ai instead.", file=sys.stderr)
            emit(run_crawl4ai(url))
            return
        print("Error: trafilatura not found. Install with: uv tool install trafilatura", file=sys.stderr)
        sys.exit(1)

    output = run_trafilatura(url)
    verdict = classify(output)

    if verdict == "ok":
        emit(output)
        return

    # Thin or blocked. A browser can sometimes clear a JS challenge a plain HTTP client
    # cannot, so escalation is worth one attempt even when the verdict is already "blocked".
    if not check_crawl4ai():
        if verdict == "blocked":
            exit_blocked(output)
        print(
            "Error: trafilatura returned a thin result and crawl4ai is not installed. "
            "Install it for JS rendering: uv tool install crawl4ai && crawl4ai-setup",
            file=sys.stderr,
        )
        sys.exit(2)

    reason = "was blocked" if verdict == "blocked" else "returned thin content"
    print(f"Trafilatura {reason}, escalating to crawl4ai (JS rendering).", file=sys.stderr)
    escalated = run_crawl4ai(url)

    # Escalation must not lose ground: crawl4ai can come back emptier than trafilatura did.
    if classify(escalated) == "ok" or len(escalated) >= len(output):
        emit(escalated)
    else:
        emit(output)


if __name__ == "__main__":
    main()
