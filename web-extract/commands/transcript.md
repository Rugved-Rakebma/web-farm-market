---
description: Extract transcript and metadata from a video URL (YouTube, Vimeo, Twitter, TikTok, etc.)
argument-hint: <video-url> [--timestamps] [--lang <code>]
---

## Process

Extract transcript from: **$ARGUMENTS**

1. **Validate URL.** If `$ARGUMENTS` is empty, ask the user for a video URL.

2. **Run the transcript script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-transcript.py "$ARGUMENTS"
   ```
   The script handles metadata extraction, caption download (auto-subs → manual subs fallback), and json3/VTT-to-plaintext conversion.

   Optional flags: `--timestamps` emits timestamped paragraphs instead of one flat block (use it for long videos you intend to cite or archive); `--lang <code>` selects a caption language (default `en`).

3. **Present the result** to the user in two sections:

   **Metadata** — title, channel/author, duration, upload date, view count, description.

   **Transcript** — the full transcript text. If long, note the word count.

4. **Handle errors:**
   - Exit code 2 (unsupported URL) → tell the user yt-dlp doesn't support this site, suggest `/web-x:fetch` instead
   - "No transcript available" in output → report that no subtitles exist for this video
   - Network errors → report and suggest retrying
   - **"failed on all player clients"** → the script already walked its full client chain. This is an IP-level throttle on YouTube's `/watch` endpoint, not an auth problem. Tell the user to wait ~30–60 min or try another network. **Never suggest `--cookies-from-browser`** — it requires the browser's master cookie-encryption key (which decrypts every site's cookies) and risks a YouTube account ban per yt-dlp's own FAQ.

## Notes

- Auto-generated captions garble proper nouns badly (names, product names, jargon). When presenting a transcript, flag this and correct obvious mangles rather than quoting them verbatim.
- If yt-dlp warns it is >90 days old, run `uv tool upgrade yt-dlp` — YouTube changes extraction surfaces frequently.
