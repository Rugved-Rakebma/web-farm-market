#!/usr/bin/env python3
"""Extract clean markdown from a web page via a three-tier escalation ladder.

Usage: python3 web-fetch.py <url> [--js] [--stealth]

  (default)   tier 1 -> escalates on its own
  --js        start at tier 2 (skip the no-browser attempt)
  --stealth   go straight to tier 3 (skip straight to the anti-bot browser)

Exit codes: 0=success, 1=backend missing, 2=extraction failed, 3=blocked by anti-bot.

The ladder
----------
    tier 1  trafilatura                      <1s    default
    tier 2  crawl4ai (headless Chromium)     3-5s   on THIN  (page needs JS)
    tier 3  scrapling stealthy-fetch         9-30s  on BLOCKED (site refused us)

Each tier is the best available tool for its own job, not a general-purpose fallback:

* trafilatura stays tier 1 because it is a boilerplate-removal specialist and measurably
  beats the alternatives at it. Benchmarked 2026-09-03 against `scrapling extract get
  --ai-targeted`: on paulgraham.com/greatwork.html trafilatura returns clean prose while
  scrapling converts the page's 1990s layout tables into ~8KB of markdown table scaffolding;
  on simonwillison.net scrapling leaks the masthead, the Subscribe link and a sponsor ad
  block that trafilatura drops. Do not "simplify" by folding tier 1 into scrapling.

* crawl4ai stays tier 2 because it is already required by web-crawl.py, so it costs nothing
  extra, and it resolves relative links to absolute URLs where `scrapling extract fetch`
  leaves them relative. Relative links are broken links once vault-x archives the page.
  Rendering quality is otherwise equivalent (verified on quotes.toscrape.com/js).

* scrapling is tier 3 ONLY. It is the sole backend here that can clear an anti-bot
  challenge — verified against nopecha.com/demo/cloudflare, where it solved an interactive
  Turnstile in 9.2s and returned 26KB of real page content. Its weaker article extraction
  never matters at this tier, because the alternative at this tier is nothing at all.

Why output is classified, not measured
--------------------------------------
Anti-bot systems answer with HTTP 200 and a fully-formed *challenge* page. Cloudflare's
interstitial renders to ~500 chars of markdown — comfortably over any "is this thin?"
threshold — so a length check alone hands the challenge page back to the caller as if it
were the article. Verified against nopecha.com/demo/cloudflare before this was added:
495 bytes, exit 0, body reading "Performing security verification ... Ray ID: a32e1c72...".

That is worse than an error. An error stops the caller; a silent wrong answer gets
summarised, cited, and archived into a vault as though it were a source.

Same failure class as the YouTube 429 that web-transcript.py handles, which arrives
disguised as "Sign in to confirm you're not a bot" — a block that does not look like a
block. Same remedy: match content signatures, not lengths.

classify() returns "ok", "thin", or "blocked". Blocked requires BOTH a short body AND a
challenge-page signature. The pairing is load-bearing: an article *about* Cloudflare
contains the word and would false-positive on signature alone, but runs to thousands of
characters. Verified: Scrapling's own stealth-fetching docs page mentions Cloudflare 26
times and classifies "ok" at 22,972 bytes.

Known gap: no prompt-injection sanitising
-----------------------------------------
Output is NOT stripped of CSS-hidden text, aria-hidden nodes or zero-width unicode, any of
which can carry instructions aimed at whatever model reads the result. Tier 3 gets this via
scrapling's --ai-targeted, but tiers 1 and 2 do not, so the pipeline as a whole does not.
Treat every result as untrusted input. A real fix is a sanitising pass over the emitted
markdown, applied at all three tiers; it is deliberately not half-done here.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

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

INSTALL_HINTS = {
    "trafilatura": "uv tool install trafilatura",
    "crawl4ai": "uv tool install crawl4ai && crawl4ai-setup",
    "scrapling": 'uv tool install "scrapling[fetchers,rag]" && scrapling install',
}


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


def have(tool: str) -> bool:
    return shutil.which({"crawl4ai": "crwl"}.get(tool, tool)) is not None


def exit_blocked(text: str, tried_stealth: bool) -> None:
    marker = matched_marker(text) or "unknown"
    tail = (
        "Tier 3 (scrapling stealthy-fetch) was tried and still could not get through."
        if tried_stealth
        else f"Tier 3 needs scrapling. Install: {INSTALL_HINTS['scrapling']}"
    )
    print(
        f'Error: blocked by an anti-bot challenge (matched: "{marker}").\n'
        "The site returned a challenge page, not content — this is a refusal, not an "
        "extraction failure, so the page body is deliberately NOT printed.\n"
        f"{tail}\n"
        "Options: retry in a while, try a different network, or open the page manually.",
        file=sys.stderr,
    )
    sys.exit(3)


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


def run_scrapling_stealth(url: str) -> str:
    """Tier 3. scrapling writes to a file rather than stdout, hence the tempdir."""
    tmpdir = tempfile.mkdtemp()
    out_path = os.path.join(tmpdir, "page.md")
    try:
        result = subprocess.run(
            ["scrapling", "extract", "stealthy-fetch", url, out_path,
             "--solve-cloudflare", "--ai-targeted"],
            capture_output=True, text=True,
        )
        if not os.path.exists(out_path):
            print(
                f"Error: scrapling stealthy-fetch failed: {result.stderr.strip()[-500:]}",
                file=sys.stderr,
            )
            sys.exit(2)
        with open(out_path, encoding="utf-8") as fh:
            return fh.read().strip()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def emit(text: str) -> None:
    """Final gate and the only exit on success. Nothing reaches stdout unclassified.

    Terminal by design: it exits rather than returns. An earlier revision let emit() fall
    through, so after tier 3 printed a good page control resumed in the caller and re-emitted
    the *blocked* tier-2 body — stdout got 26KB of correct content alongside exit 3. Ending
    the process here makes that whole class of fall-through unreachable.
    """
    if classify(text) == "blocked":
        exit_blocked(text, tried_stealth=True)
    if not text:
        print("Error: extraction returned an empty result.", file=sys.stderr)
        sys.exit(2)
    print(text)
    sys.exit(0)


def tier3(url: str, prior: str) -> None:
    """Blocked. Only scrapling can clear a challenge; without it this is terminal."""
    if not have("scrapling"):
        exit_blocked(prior, tried_stealth=False)
    print("Blocked — escalating to scrapling stealthy-fetch (solving challenge).",
          file=sys.stderr)
    emit(run_scrapling_stealth(url))


def require(tool: str) -> None:
    if not have(tool):
        print(f"Error: {tool} not found. Install with: {INSTALL_HINTS[tool]}",
              file=sys.stderr)
        sys.exit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 web-fetch.py <url> [--js] [--stealth]", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    flags = sys.argv[2:]

    if "--stealth" in flags:
        require("scrapling")
        emit(run_scrapling_stealth(url))
        return

    if "--js" in flags:
        require("crawl4ai")
        rendered = run_crawl4ai(url)
        if classify(rendered) == "blocked":
            tier3(url, rendered)
        emit(rendered)
        return

    # Tier 1.
    if not have("trafilatura"):
        if not have("crawl4ai"):
            require("trafilatura")
        print("trafilatura not found, starting at crawl4ai instead.", file=sys.stderr)
        rendered = run_crawl4ai(url)
        if classify(rendered) == "blocked":
            tier3(url, rendered)
        emit(rendered)
        return

    output = run_trafilatura(url)
    verdict = classify(output)

    if verdict == "ok":
        emit(output)
        return

    # Tier 2. A browser can sometimes clear a JS challenge a plain HTTP client cannot, so
    # escalation is worth one attempt even when the verdict is already "blocked".
    if not have("crawl4ai"):
        if verdict == "blocked":
            tier3(url, output)
        print(
            "Error: trafilatura returned a thin result and crawl4ai is not installed. "
            f"Install it for JS rendering: {INSTALL_HINTS['crawl4ai']}",
            file=sys.stderr,
        )
        sys.exit(2)

    reason = "was blocked" if verdict == "blocked" else "returned thin content"
    print(f"Trafilatura {reason}, escalating to crawl4ai (JS rendering).", file=sys.stderr)
    rendered = run_crawl4ai(url)

    if classify(rendered) == "blocked":
        tier3(url, rendered)

    # Escalation must not lose ground: crawl4ai can come back emptier than trafilatura did.
    emit(rendered if classify(rendered) == "ok" or len(rendered) >= len(output) else output)


if __name__ == "__main__":
    main()
