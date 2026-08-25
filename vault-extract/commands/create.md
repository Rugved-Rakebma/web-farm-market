---
description: Create a new vault inside the federation
argument-hint: <name> [--purpose "..."] [--root <path>]
---

## Process

Create vault: **$ARGUMENTS**

1. **Parse args.** Extract `<name>` (required). Optional: `--purpose`, `--root`.

2. **If `--purpose` is not provided,** ask the user for a one-sentence purpose before running the script. This lands in the `overview.md` frontmatter and is surfaced by `/vault-x:list`.

3. **Run the create script:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-create.py $ARGUMENTS
   ```

4. **Report** the new vault path and the two scaffolded files (`overview.md`, `CLAUDE.md`).

5. **Remind the user** to open the new vault directory once in Obsidian to register it ("Open folder as vault" in the vault switcher).

## Notes

- `create` always produces a **tier-1** vault: `<name>-vault/` at the federation root
  (the suffix is appended if not present). The `-vault` suffix **is** the tier-1 marker.
- `-vault` must never appear inside a classifier directory — the classifier already names
  the kind, so tier-2 slugs carry no suffix. The script refuses a name containing a path
  separator, so `create research/foo` fails rather than doing something surprising.
- **To promote an existing tier-2 vault instead of starting fresh, use
  `/vault-x:graduate`.** `create` starts empty; `graduate` moves one that already earned
  it. Same destination, different histories.
- The script refuses (exit 5) if the same topic already exists at the other tier, and
  prints the `git mv` that graduation would use — creating a second vault for one topic
  is the thing the two-tier standard exists to prevent.
- The script does NOT pre-create `source/` or any subdirectories — the vault's internal layout is a decision made when the vault is designed.
- The script does NOT programmatically register the vault with Obsidian's `obsidian.json` config.
