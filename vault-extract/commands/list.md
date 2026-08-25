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

- The script does a **bounded two-level scan** of `<root>`, finding vaults at exactly two positions: tier-1 `<name>-vault/` and tier-2 `<classifier>/<slug>/`. Output is grouped by tier. Directories without an `overview.md` — run folders, `sources/`, `records/` — are contents, not vaults, and never appear.
- **Tier is readable from the name:** a `/` means tier 2; a `-vault` suffix means tier 1.
- An **Anomalies** section lists placements that violate the two-tier standard (a `-vault` directory with no `overview.md`, a vault at the root without the suffix, a tier-2 vault carrying one). These are not resolvable as vaults — report them to the user; the fix is a rename or a move.
