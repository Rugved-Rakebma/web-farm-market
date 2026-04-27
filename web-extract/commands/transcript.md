---
description: Extract transcript and metadata from a video URL (YouTube, Vimeo, Twitter, TikTok, etc.)
argument-hint: <video-url>
---

## Process

Extract transcript from: **$ARGUMENTS**

1. **Validate URL.** If `$ARGUMENTS` is empty, ask the user for a video URL.

2. **Run the transcript script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/web-transcript.py "$ARGUMENTS"
   ```
   The script handles metadata extraction, subtitle download (auto-subs → manual subs fallback), and VTT-to-plaintext conversion.

3. **Present the result** to the user in two sections:

   **Metadata** — title, channel/author, duration, upload date, view count, description.

   **Transcript** — the full transcript text. If long, note the word count.

4. **Handle errors:**
   - Exit code 2 (unsupported URL) → tell the user yt-dlp doesn't support this site, suggest `/web-x:fetch` instead
   - "No transcript available" in output → report that no subtitles exist for this video
   - Network errors → report and suggest retrying
