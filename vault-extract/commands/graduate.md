---
description: Graduate a tier-2 classified vault into a tier-1 hand-maintained vault
argument-hint: <classifier/slug> [--name <vault-name>] [--domain "..."] [--root <path>]
---

## Process

Graduate the vault: **$ARGUMENTS**

Graduation moves a vault out from under a classifier's tooling and makes it
hand-maintained. It is **one-way** — there is no `ungraduate`. Confirm before the move;
after it, the vault is yours to shape.

1. **Parse args.** The source vault reference is required (`research/local-llms`, or a
   bare slug). Optional: `--name` (the tier-1 name; defaults to the slug), `--domain`,
   `--root`. If no reference is given, run `/vault-x:list` and ask which vault.

2. **Read the vault before deciding anything.** Run
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-view.py <ref> [--root <path>]`, then read
   its `overview.md` and `CLAUDE.md`. Step 6 depends on knowing what this vault actually
   holds, and you cannot outsource that to the script.

3. **Apply the graduation test yourself, out loud.** State in one short paragraph:
   *could a fresh run of the classifier's tooling reproduce this vault?* Name the
   specific content that makes the answer **no** — private records, live decision
   documents, distilled positions. If the answer is **yes**, say so and stop. Graduation
   is not a promotion you spend on a lab notebook that merely got large.

4. **Dry-run the script.** It re-checks your judgement structurally and refuses if it
   finds nothing the tooling couldn't have written:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/vault-graduate.py <ref> \
     [--name <vault-name>] [--domain "<domain>"] [--root <path>] --dry-run
   ```
   Show the user the plan it prints: source → destination, the move mechanism it
   detected, the reproducibility audit, and every frontmatter key it will change.

   **Always pass `--domain`.** Without it the script writes `domain: TODO`. The domain
   is this vault's own subject, never the classifier it left.

5. **Confirm — never graduate silently.** Ask with `AskUserQuestion` (header
   "Graduate"):
   - option 1 — *"Graduate to `<name>-vault`"*, labelled "(Recommended)" only if your
     step-3 answer was **no** (not reproducible);
   - option 2 — *"Keep at `<classifier>/<slug>`"*, with your one-line reason;
   - option 3 — *"Graduate under a different name"* (the user types it via "Other").

   State plainly in the question body that this is **one-way** and that it rewrites
   `CLAUDE.md`.

   On confirmation, re-run the same command **without** `--dry-run`.

6. **Write the vault's layers into `CLAUDE.md`.** The script left a marked block:
   ```
   <!-- vault-x:graduate:layers -->
   ...
   <!-- /vault-x:graduate:layers -->
   ```
   Replace that entire block — markers included. It already lists the audit's
   unreproducible entries as your raw material. It must end up stating:
   - **what each hand-maintained layer is** and who maintains it (you, not the tooling);
   - **which parts the classifier's tooling still writes**, and that it no longer owns
     the vault's shape;
   - **frontmatter `type:` values** for the hand-maintained files — extend the run-file
     schema already in the file, don't replace it;
   - **wiki-link practice** if the vault now links across folders (run folders stay
     hermetic; root-level documents may link down into a run's `report.md` to cite
     evidence, and runs never link back up);
   - **anything sensitive** the vault holds, where it lives, and where it may not go.

   Also fill in the `## Layout` tree — the script pre-populated it with the vault's real
   entries and marked the hand-maintained ones `Claude: describe this`.

   `~/knowledge-vaults/personal-tax-vault/CLAUDE.md` is the worked example of all five.

7. **Write the layers into `overview.md`.** Replace the
   `<!-- vault-x:graduate:overview -->` block with prose describing the added layers, and
   confirm `domain:` names this vault's own subject. If it says `TODO`, fix it now.

8. **Report.** Print the new path, the two files you rewrote, and the new commands:
   `/vault-x:view <name>-vault`, `/vault-x:research "<q>"` (it can now target this
   vault), `/vault-x:grow <name>-vault`. If the script wrote a `CLAUDE.md.pre-graduation`
   sidecar, say so and offer to reconcile it. **If the script reported that the move was
   not recorded in version control, surface its staging command verbatim** — the move is
   not tracked until the user runs it.

## Notes

- **One-way.** A tier-1 vault never returns to a classifier. If you graduate by mistake,
  the fix is a manual `git mv` back plus reverting both files — the plugin won't do it.
- **Graduation does not end the tooling relationship.** `/vault-x:research` and
  `/vault-x:grow` both still target a tier-1 vault, and runs land there as ordinary dated
  folders. What changes is ownership: the classifier's tooling no longer owns the vault's
  shape, and hand-maintained layers win over any single run.
- **`create` vs `graduate`.** `/vault-x:create` starts a tier-1 vault empty. `graduate`
  promotes one that already earned it. Same destination, different histories.
- **The audit is a necessary condition, not the test.** It enumerates what the tooling
  could not have written. An empty set is a refusal; a non-empty set is not an approval.
  Judgement stays in step 3.
- The script never merges into an existing directory, never commits, and refuses to
  overwrite a `CLAUDE.md` that was hand-edited (it sidecars it as
  `CLAUDE.md.pre-graduation` instead — an extension the vault tools ignore).
- **Re-running on an already-graduated vault exits 0** and does nothing, so the command
  is safe to retry.
