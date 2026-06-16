# Vault Extract — Development Guide

## Architecture

Manages a federation of structured knowledge-base vaults at `~/knowledge-vaults/`. Plugin slug `"vault-x"` creates the `/vault-x:` prefix.

Two layers:

1. **Commands** (`/vault-x:*`) — User-invocable workflows in `commands/`. Each calls a Python script via `${CLAUDE_PLUGIN_ROOT}/scripts/`.
2. **Scripts** — Python orchestration in `scripts/`. Read template files from `templates/` at scaffold time.

## Plugin Structure

```
commands/           # /vault-x:init, /vault-x:create, /vault-x:list, /vault-x:view
scripts/            # Python implementations (uses pyyaml)
  vault-init.py     # Scaffold federation root + CLAUDE.md
  vault-create.py   # Scaffold a new vault dir + overview.md + CLAUDE.md + .obsidian/
  vault-list.py     # Federation overview (read every overview.md frontmatter)
  vault-view.py     # Single-vault map (frontmatter + dir tree + wiki-link graph)
templates/          # Files written by init/create
  federation-CLAUDE.md
  vault-CLAUDE.md
  vault-overview.md
```

## Prerequisites

- Python 3.9+
- `pyyaml` — for frontmatter parsing. Install: `pip install pyyaml` or `uv pip install pyyaml`.

## Federation root

Default: `~/knowledge-vaults/`. Override with `--root <path>` on any command.

## Substrate the tools rely on

Every file in a managed vault carries YAML frontmatter (schema declared per-vault in its `CLAUDE.md`). Files reference each other via `[[wiki-links]]`, hermetic per vault. The tool layer walks the filesystem on demand — nothing is pre-indexed.

## Testing

```bash
python3 scripts/vault-init.py --root /tmp/test-kv
python3 scripts/vault-create.py my-vault --root /tmp/test-kv --purpose "A test vault."
python3 scripts/vault-list.py --root /tmp/test-kv
python3 scripts/vault-view.py my-vault --root /tmp/test-kv
```

## Architecture decisions

See `../docs/vault-plugin-planning.md` for design rationale and the decisions log.
