---
description: Initialize the knowledge-vaults federation root at ~/knowledge-vaults/
argument-hint: [--root <path>]
---

## Process

1. **Run the init script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-init.py $ARGUMENTS
   ```
   Default federation root: `~/knowledge-vaults/`. Override with `--root <path>`.

2. **Report** the federation root location and confirm the scaffolded `CLAUDE.md`.

3. **Suggest next step:** create the first vault with `/vault-x:create <name>`.

## Notes

- Idempotent — if the root already has a `CLAUDE.md`, the script no-ops with a message. Add `--force` to overwrite.
