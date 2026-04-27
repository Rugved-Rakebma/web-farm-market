#!/usr/bin/env python3
"""Extract transcript + metadata from a video URL via yt-dlp.

Usage: python3 web-transcript.py <url>

Outputs metadata and plain-text transcript to stdout.
Errors go to stderr. Exit codes: 0=success, 1=yt-dlp missing, 2=unsupported URL.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def check_ytdlp() -> None:
    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp not found. Install with: uv tool install yt-dlp", file=sys.stderr)
        sys.exit(1)


def extract_metadata(url: str) -> dict | None:
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-warnings", url],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        if "Unsupported URL" in result.stderr or "is not a valid URL" in result.stderr:
            print(f"Error: Unsupported URL — yt-dlp cannot handle: {url}", file=sys.stderr)
            sys.exit(2)
        print(f"Error: yt-dlp failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(2)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Error: Could not parse yt-dlp JSON output", file=sys.stderr)
        sys.exit(2)


def print_metadata(data: dict) -> None:
    print("=== METADATA ===")
    print(f"Title: {data.get('title', 'N/A')}")
    print(f"Channel: {data.get('channel', data.get('uploader', 'N/A'))}")
    print(f"Duration: {data.get('duration_string', 'N/A')}")
    print(f"Upload Date: {data.get('upload_date', 'N/A')}")
    print(f"View Count: {data.get('view_count', 'N/A')}")
    desc = (data.get("description", "") or "")[:500]
    if desc:
        print(f"Description: {desc}")
    print()


def download_subs(url: str, tmpdir: str) -> str | None:
    """Try auto-generated subs, then manual subs. Returns path to VTT file or None."""
    out_template = os.path.join(tmpdir, "sub")

    # Try auto-generated first
    result = subprocess.run(
        ["yt-dlp", "--write-auto-subs", "--sub-lang", "en",
         "--skip-download", "--sub-format", "vtt",
         "-o", out_template, "--no-warnings", "--quiet", url],
        capture_output=True, text=True,
    )

    # Check for VTT file
    vtt = _find_vtt(tmpdir)
    if vtt:
        return vtt

    # Try manual subs
    result = subprocess.run(
        ["yt-dlp", "--write-subs", "--sub-lang", "en",
         "--skip-download", "--sub-format", "vtt",
         "-o", out_template, "--no-warnings", "--quiet", url],
        capture_output=True, text=True,
    )

    return _find_vtt(tmpdir)


def _find_vtt(directory: str) -> str | None:
    for f in Path(directory).glob("*.vtt"):
        return str(f)
    return None


def vtt_to_text(vtt_path: str) -> str:
    """Parse VTT subtitle file to clean plain text."""
    text = Path(vtt_path).read_text(encoding="utf-8")
    lines = text.split("\n")
    out: list[str] = []

    for line in lines:
        line = line.strip()
        # Skip empty lines, headers, timestamps, numeric indices
        if not line:
            continue
        if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if re.match(r"^\d{2}:\d{2}", line):
            continue
        if re.match(r"^\d+$", line):
            continue
        # Strip HTML/formatting tags
        line = re.sub(r"<[^>]+>", "", line)
        # Deduplicate consecutive identical lines
        if line and (not out or out[-1] != line):
            out.append(line)

    return " ".join(out)


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 web-transcript.py <url>", file=sys.stderr)
        sys.exit(1)

    url = sys.argv[1]
    check_ytdlp()

    # Metadata
    data = extract_metadata(url)
    if data:
        print_metadata(data)

    # Transcript
    print("=== TRANSCRIPT ===")
    tmpdir = tempfile.mkdtemp()
    try:
        vtt_path = download_subs(url, tmpdir)
        if vtt_path:
            transcript = vtt_to_text(vtt_path)
            print(transcript)
        else:
            print("No transcript available for this video.")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
