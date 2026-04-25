---
description: Extract transcript and metadata from a video URL (YouTube, Vimeo, Twitter, TikTok, etc.)
argument-hint: <video-url>
---

## Process

Extract transcript from: **$ARGUMENTS**

1. **Validate URL.** If `$ARGUMENTS` is empty, ask the user for a video URL.

2. **Run yt-dlp:**
   ```bash
   just web-transcript "$ARGUMENTS"
   ```

3. **Present the result** to the user in two sections:

   **Metadata** — title, channel/author, duration, upload date, view count, description (truncated if very long).

   **Transcript** — the full transcript text. If long, present it as a collapsible section or note the word count.

4. **Handle errors:**
   - "is not a valid URL" or "Unsupported URL" → tell the user yt-dlp doesn't support this site, suggest `/web-x:fetch` instead
   - "No subtitles" or empty transcript → report that no transcript is available for this video (auto-generated or manual)
   - Network errors → report and suggest retrying
