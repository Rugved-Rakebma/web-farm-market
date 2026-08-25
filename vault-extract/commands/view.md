---
description: Show the dynamic map of a single vault (dir tree + frontmatter + wiki-link graph)
argument-hint: <vault> (path, name, or slug) [--root <path>]
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

- The argument is a **vault reference**: a path relative to the federation root (`research/local-llms`), a tier-1 name with or without the suffix (`personal-tax-vault`, `personal-tax`), or a unique leaf slug.
- **A reference stops at the vault directory.** `research` (a classifier) and `research/local-llms/2026-01-01-foo` (a run folder) are not vaults; the script says so and names the real vault.
- **An ambiguous bare slug is an error, not a guess** (exit 4). If a slug matches vaults at both tiers, pass the full reference — and treat the collision as a bug: a topic should exist at exactly one tier.
- The script parses YAML frontmatter from every `.md` file (except `overview.md` and `CLAUDE.md`) and extracts `[[wiki-links]]` from bodies.
- For an empty vault (no content beyond scaffold), output is the purpose + dir tree + "no content yet" marker.
