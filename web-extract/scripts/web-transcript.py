#!/usr/bin/env python3
"""Extract transcript + metadata from a video URL via yt-dlp.

Usage: python3 web-transcript.py <url> [--timestamps] [--lang en]

Outputs metadata and plain-text transcript to stdout.
Errors go to stderr. Exit codes: 0=success, 1=yt-dlp missing, 2=unsupported/blocked URL.

Why the player-client chain
---------------------------
yt-dlp's default YouTube clients are ('visionos', 'web'). The `web` client scrapes the
`/watch` HTML page, which YouTube aggressively rate-limits: once an IP trips the
threshold, `/watch` 302-redirects to `google.com/sorry/index` and returns HTTP 429.
yt-dlp surfaces that as "Sign in to confirm you're not a bot", which misleadingly
implies an auth problem. It is an IP throttle on one endpoint, not an account issue.

The mobile/TV clients (android, visionos, android_vr, ios) talk to the InnerTube
player API instead and never touch `/watch`, so they keep working through the throttle.
Captions live on the `timedtext` path, which is not gated the way media streams are —
so transcript extraction survives even when format/stream extraction does not.

Never solve this with `--cookies-from-browser`: it requires the browser's master cookie
encryption key (macOS keychain "Chrome Safe Storage"), which decrypts cookies for EVERY
site, not just YouTube. yt-dlp's own FAQ also warns that using account cookies risks
the account being banned. The client chain below needs no credentials at all.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ordered by observed reliability under an IP throttle. Each of these reaches the
# InnerTube player API directly. "default" is last so behaviour degrades to stock
# yt-dlp rather than failing outright if YouTube retires the mobile clients.
CLIENT_CHAIN = ("android", "visionos", "android_vr", "ios", "web_embedded", "default")

# yt-dlp only auto-detects deno. Node and bun work fine but must be named explicitly.
JS_RUNTIMES = ("deno", "node", "bun")

BOT_GATE_MARKERS = (
    "Sign in to confirm",
    "429",
    "Too Many Requests",
    "The page needs to be reloaded",
    "not a bot",
)


def check_ytdlp() -> None:
    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp not found. Install with: uv tool install yt-dlp", file=sys.stderr)
        sys.exit(1)


def js_runtime_args() -> list[str]:
    """Point yt-dlp at whatever JS runtime exists; silences the EJS deprecation warning."""
    found = [r for r in JS_RUNTIMES if shutil.which(r)]
    return ["--js-runtimes", ",".join(found)] if found else []


def base_args(client: str) -> list[str]:
    args = ["yt-dlp", "--no-warnings", "--socket-timeout", "30", "--sleep-requests", "1"]
    args += js_runtime_args()
    if client != "default":
        args += ["--extractor-args", f"youtube:player_client={client}"]
    return args


def is_blocked(stderr: str) -> bool:
    return any(m in stderr for m in BOT_GATE_MARKERS)


def extract_metadata(url: str) -> tuple[dict | None, str]:
    """Walk the client chain until one returns parseable JSON. Returns (data, client)."""
    last_err = ""
    for client in CLIENT_CHAIN:
        result = subprocess.run(
            base_args(client) + ["--dump-json", "--skip-download", url],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                return json.loads(result.stdout.splitlines()[0]), client
            except json.JSONDecodeError:
                pass
        last_err = result.stderr.strip()
        if "Unsupported URL" in last_err or "is not a valid URL" in last_err:
            print(f"Error: Unsupported URL — yt-dlp cannot handle: {url}", file=sys.stderr)
            sys.exit(2)
        if not is_blocked(last_err):
            # A real failure (private/deleted video); trying other clients won't help.
            break

    print(f"Error: yt-dlp failed on all player clients. Last error:\n{last_err}", file=sys.stderr)
    if is_blocked(last_err):
        print(
            "\nThis is an IP-level rate limit on YouTube's /watch endpoint, not an auth problem.\n"
            "Options: wait ~30-60 min for the throttle to clear, or try from another network.\n"
            "Do NOT pass --cookies-from-browser: it exposes every site's cookies and risks an "
            "account ban (see yt-dlp FAQ).",
            file=sys.stderr,
        )
    sys.exit(2)


def print_metadata(data: dict, client: str) -> None:
    print("=== METADATA ===")
    print(f"Title: {data.get('title', 'N/A')}")
    print(f"Channel: {data.get('channel', data.get('uploader', 'N/A'))}")
    print(f"Duration: {data.get('duration_string', 'N/A')}")
    print(f"Upload Date: {data.get('upload_date', 'N/A')}")
    print(f"View Count: {data.get('view_count', 'N/A')}")
    print(f"URL: {data.get('webpage_url', 'N/A')}")
    desc = (data.get("description", "") or "")[:500]
    if desc:
        print(f"Description: {desc}")
    print(f"[extracted via player_client={client}]")
    print()


def download_subs(url: str, tmpdir: str, lang: str, client: str) -> str | None:
    """Fetch captions. Prefers json3 (clean segments) over vtt (rolling duplicates).

    Tries the client that already worked for metadata first, then the rest of the chain.
    """
    out_template = os.path.join(tmpdir, "sub")
    order = [client] + [c for c in CLIENT_CHAIN if c != client]

    for c in order:
        for flag in ("--write-auto-subs", "--write-subs"):
            subprocess.run(
                base_args(c) + [
                    flag, "--sub-langs", f"{lang}.*,{lang}",
                    "--skip-download", "--sub-format", "json3/vtt/best",
                    "-o", out_template, "--quiet", url,
                ],
                capture_output=True, text=True,
            )
            found = _find_sub(tmpdir)
            if found:
                return found
    return None


def _find_sub(directory: str) -> str | None:
    for ext in ("*.json3", "*.vtt"):
        for f in sorted(Path(directory).glob(ext)):
            return str(f)
    return None


def _ts(ms: int) -> str:
    s = int(ms / 1000)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def json3_to_text(path: str, timestamps: bool) -> str:
    """json3 gives discrete non-overlapping segments — no rolling-duplicate problem."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segs: list[tuple[int, str]] = []
    for event in data.get("events", []):
        parts = event.get("segs")
        if not parts:
            continue
        text = "".join(p.get("utf8", "") for p in parts).replace("\n", " ")
        if text.strip():
            segs.append((event.get("tStartMs", 0), text))

    if not segs:
        return ""
    if not timestamps:
        return re.sub(r"\s+", " ", "".join(t for _, t in segs)).strip()

    out, cur, start = [], [], segs[0][0]
    for ms, text in segs:
        if ms - start >= 45000 and cur:
            out.append(f"**[{_ts(start)}]** {re.sub(r'\s+', ' ', ''.join(cur)).strip()}")
            cur, start = [], ms
        cur.append(text)
    if cur:
        out.append(f"**[{_ts(start)}]** {re.sub(r'\s+', ' ', ''.join(cur)).strip()}")
    return "\n\n".join(out)


def vtt_to_text(vtt_path: str) -> str:
    """Fallback parser. VTT auto-captions roll, so consecutive duplicates are stripped."""
    out: list[str] = []
    for line in Path(vtt_path).read_text(encoding="utf-8").split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if re.match(r"^\d{2}:\d{2}", line) or re.match(r"^\d+$", line):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and (not out or out[-1] != line):
            out.append(line)
    return " ".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract transcript + metadata from a video URL.")
    ap.add_argument("url")
    ap.add_argument("--lang", default="en", help="Caption language code (default: en)")
    ap.add_argument("--timestamps", action="store_true",
                    help="Emit timestamped paragraphs instead of one flat block")
    args = ap.parse_args()

    check_ytdlp()

    data, client = extract_metadata(args.url)
    if data:
        print_metadata(data, client)

    print("=== TRANSCRIPT ===")
    tmpdir = tempfile.mkdtemp()
    try:
        sub_path = download_subs(args.url, tmpdir, args.lang, client)
        if not sub_path:
            print(f"No transcript available for this video (language: {args.lang}).")
            return
        text = (json3_to_text(sub_path, args.timestamps)
                if sub_path.endswith(".json3") else vtt_to_text(sub_path))
        print(text if text.strip() else "Transcript file was empty.")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
