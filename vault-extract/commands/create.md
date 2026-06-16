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

- The script names the directory `<name>-vault/` (appending `-vault` if not present).
- The script does NOT pre-create `source/` or any subdirectories — the vault's internal layout is a decision made when the vault is designed.
- The script does NOT programmatically register the vault with Obsidian's `obsidian.json` config.
