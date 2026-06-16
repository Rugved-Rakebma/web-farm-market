---
description: Show the dynamic map of a single vault (dir tree + frontmatter + wiki-link graph)
argument-hint: <vault-name> [--root <path>]
---

## Process

View vault: **$ARGUMENTS**

1. **Run the view script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-view.py $ARGUMENTS
   ```

2. **Use the output** to identify which files in the vault are relevant. The file list shows title + frontmatter highlights; the link graph shows relationships; orphans are flagged.

3. **For any file Claude needs to read in depth,** use the standard `Read` tool with the path shown.

## Notes

- The script parses YAML frontmatter from every `.md` file (except `overview.md` and `CLAUDE.md`) and extracts `[[wiki-links]]` from bodies.
- For an empty vault (no content beyond scaffold), output is the purpose + dir tree + "no content yet" marker.
