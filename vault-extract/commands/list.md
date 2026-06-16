---
description: List all vaults in the federation with their purposes
argument-hint: [--root <path>]
---

## Process

1. **Run the list script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-list.py $ARGUMENTS
   ```

2. **Present** the output to the user.

3. **If the user is picking a vault for a task,** suggest based on purpose/topics match. If no good match, suggest `/vault-x:create <name>` for a new one.

## Notes

- The script walks `<root>/*/overview.md` and aggregates the frontmatter. Vaults without an `overview.md` are skipped.
