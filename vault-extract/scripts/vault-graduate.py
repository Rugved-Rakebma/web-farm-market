#!/usr/bin/env python3
"""Graduate a tier-2 classified vault into a tier-1 hand-maintained vault.

Usage:
  vault-graduate.py <ref> [--name <vault-name>] [--domain "..."]
      [--root <path>] [--dry-run] [--force]
      [--git-dir <path> --work-tree <path> | --no-git]

Graduation moves a vault out from under a classifier's tooling and makes it
hand-maintained. It is ONE-WAY.

This script does the deterministic half: validate, audit, rewrite overview.md's
frontmatter, drop the tier-1 CLAUDE.md template in place with marker blocks, and
move the directory. Claude then fills the marker blocks, because only it knows
what the vault earned.

The audit is a NECESSARY condition, not the graduation test. It enumerates what
the classifier's tooling could not have written; if that set is empty it refuses.
Sufficiency is a judgement call made above this script.
"""
from __future__ import annotations

import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import _common as C  # noqa: E402

RUN_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+$")
RUN_FILES = {"report.md", "blueprint.md", "sources.md"}
RUN_DIRS = {"raw"}
TOOL_TOP_FILES = {C.OVERVIEW, C.CLAUDE_MD}
TOOL_TOP_DIRS = {".obsidian", "sources"}

LAYERS_OPEN = "<!-- vault-x:graduate:layers -->"
LAYERS_CLOSE = "<!-- /vault-x:graduate:layers -->"
OVERVIEW_OPEN = "<!-- vault-x:graduate:overview -->"
OVERVIEW_CLOSE = "<!-- /vault-x:graduate:overview -->"


# ─────────────────────────── reproducibility audit ───────────────────────────

def audit(vault_dir: Path) -> tuple:
    """Split the vault's contents into tool-owned and unreproducible.

    Unreproducible = anything the classifier's tooling could not have written:
    extra root-level files, non-run directories, and any file inside a dated run
    beyond the four known names (a hand-edit inside a run is unreproducible too).
    """
    tool_owned: list = []
    unrepro: list = []

    for entry in sorted(vault_dir.iterdir(), key=lambda p: p.name):
        name = entry.name
        if name == ".DS_Store":
            continue

        if entry.is_dir():
            if name in TOOL_TOP_DIRS:
                tool_owned.append(f"{name}/")
                continue
            if RUN_DIR_RE.match(name):
                tool_owned.append(f"{name}/")
                for inner in sorted(entry.iterdir(), key=lambda p: p.name):
                    if inner.name == ".DS_Store":
                        continue
                    if inner.is_dir() and inner.name in RUN_DIRS:
                        continue
                    if inner.is_file() and inner.name in RUN_FILES:
                        continue
                    unrepro.append(f"{name}/{inner.name}"
                                   + ("/" if inner.is_dir() else ""))
                continue
            unrepro.append(f"{name}/")
            continue

        if name in TOOL_TOP_FILES:
            tool_owned.append(name)
            continue
        unrepro.append(name)

    return tool_owned, unrepro


def layout_tree(vault_dir: Path, tool_owned: list, unrepro: list) -> str:
    """A Layout block pre-populated with this vault's real top-level entries."""
    lines: list = []
    owned = set(tool_owned)
    for entry in sorted(vault_dir.iterdir(), key=lambda p: p.name):
        if entry.name in (".DS_Store", ".obsidian"):
            continue
        label = entry.name + ("/" if entry.is_dir() else "")
        if label == C.OVERVIEW:
            note = "# vault identity"
        elif label == C.CLAUDE_MD:
            note = "# this file"
        elif label == "sources/":
            note = "# tool-owned: deduped evidence library (/vault-x:grow)"
        elif RUN_DIR_RE.match(entry.name) and entry.is_dir():
            note = "# tool-owned: one research run"
        elif label in owned:
            note = "# tool-owned"
        else:
            note = "# HAND-MAINTAINED — Claude: describe this"
        lines.append(f"{label:<32}{note}")
    if not lines:
        lines.append("(empty)")
    return "\n".join(lines)


# ────────────────────────────── move mechanism ───────────────────────────────

def _git(flags: list, *args: str, cwd: Path | None = None):
    return subprocess.run(["git", *flags, *args], capture_output=True,
                          text=True, cwd=str(cwd) if cwd else None)


def resolve_git(root: Path, src: Path, args) -> tuple:
    """Find the repo that tracks `src`. Returns (flags, worktree) or (None, None).

    The federation may be tracked by a BARE repo with an external work-tree (the
    `henv` pattern), in which case there is no .git anywhere in the ancestry and a
    plain `git mv` fails. So the last resort before shutil is to probe bare repos
    in $HOME and adopt the one whose ls-files actually tracks this path — detection
    by behaviour, not by hardcoded name.
    """
    if args.no_git:
        return None, None

    if args.git_dir and args.work_tree:
        wt = Path(args.work_tree).expanduser().resolve()
        return ["--git-dir", str(Path(args.git_dir).expanduser().resolve()),
                "--work-tree", str(wt)], wt

    env_gd, env_wt = os.environ.get("VAULT_X_GIT_DIR"), os.environ.get("VAULT_X_WORK_TREE")
    if env_gd and env_wt:
        wt = Path(env_wt).expanduser().resolve()
        return ["--git-dir", str(Path(env_gd).expanduser().resolve()),
                "--work-tree", str(wt)], wt

    # ordinary repo in the ancestry
    r = _git([], "-C", str(root), "rev-parse", "--show-toplevel")
    if r.returncode == 0 and r.stdout.strip():
        top = Path(r.stdout.strip()).resolve()
        try:
            src.resolve().relative_to(top)
            return ["-C", str(top)], top
        except ValueError:
            pass

    # bare-repo probe
    home = Path.home()
    hits: list = []
    for d in sorted(home.glob(".*.git")):
        if not d.is_dir():
            continue
        b = _git(["--git-dir", str(d)], "rev-parse", "--is-bare-repository")
        if b.returncode != 0 or b.stdout.strip() != "true":
            continue
        try:
            rel = src.resolve().relative_to(home)
        except ValueError:
            continue
        ls = _git(["--git-dir", str(d), "--work-tree", str(home)],
                  "ls-files", "--", str(rel))
        if ls.returncode == 0 and ls.stdout.strip():
            hits.append(d)
    if len(hits) == 1:
        return ["--git-dir", str(hits[0]), "--work-tree", str(home)], home

    return None, None


def check_clean(flags: list, worktree: Path, src: Path) -> list:
    """Tracked changes under src. MUST pass -uall: status.showUntrackedFiles=no is
    set on the henv repo and would otherwise report a dirty tree as clean."""
    try:
        rel = src.resolve().relative_to(worktree)
    except ValueError:
        return []
    r = _git(flags, "status", "--porcelain", "-uall", "--", str(rel))
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


# ──────────────────────────────── rewrites ───────────────────────────────────

def rewrite_overview(path: Path, *, name: str, domain: str | None, today: str,
                     graduated_from: str) -> list:
    """Line-level frontmatter edits, so unrelated formatting survives byte-identical."""
    changed: list = []
    C.set_frontmatter_key(path, "name", name)
    changed.append(f"name: {name}")
    if domain:
        C.set_frontmatter_key(path, "domain", domain)
        changed.append(f"domain: {domain}")
    else:
        C.set_frontmatter_key(path, "domain", "TODO")
        changed.append("domain: TODO  ← set this")
    C.set_frontmatter_key(path, "updated", today, after="created")
    changed.append(f"updated: {today}")
    C.set_frontmatter_key(path, "graduated", today, after="updated")
    changed.append(f"graduated: {today}")
    C.set_frontmatter_key(path, "graduated_from", graduated_from, after="graduated")
    changed.append(f"graduated_from: {graduated_from}")

    # Body: replace the trailing tier-2 paragraph, or append.
    text = path.read_text(encoding="utf-8")
    block = (f"{OVERVIEW_OPEN}\n"
             f"**Graduated** from `{graduated_from}` on {today} — this vault now holds\n"
             f"content a re-run of the classifier's tooling could not reproduce.\n\n"
             f"_Claude: replace this block with a description of the layers this vault\n"
             f"carries and who maintains them. Delete the markers._\n"
             f"{OVERVIEW_CLOSE}\n")

    if OVERVIEW_OPEN in text:
        text = re.sub(re.escape(OVERVIEW_OPEN) + r".*?" + re.escape(OVERVIEW_CLOSE),
                      block.rstrip("\n"), text, flags=re.DOTALL)
    else:
        paras = text.split("\n\n")
        anchor = None
        for i in range(len(paras) - 1, -1, -1):
            low = paras[i].lower()
            if "tier-2" in low or "lab notebook, not curated knowledge" in low:
                anchor = i
                break
        if anchor is not None:
            paras[anchor] = block.rstrip("\n")
            text = "\n\n".join(paras)
        else:
            text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text, encoding="utf-8")
    changed.append("body: tier note replaced with a graduation block")
    return changed


def title_of(path: Path, fallback: str) -> str:
    """The display title from a markdown file's first H1.

    The tier-2 CLAUDE.md was rendered with a --vault-title that is not recoverable
    from overview.md's `name:` (a slug). Reading it back off the H1 is what lets
    the pristine comparison below be exact.
    """
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^#\s+(.+?)\s*$", line)
            if m:
                return m.group(1).split(" — ")[0].strip() or fallback
    return fallback


def write_tier1_claude(vault_dir: Path, *, vault_title: str, vault_name: str,
                       classifier: str, slug: str, today: str,
                       tool_owned: list, unrepro: list) -> str | None:
    """Install the tier-1 CLAUDE.md. Sidecars a hand-edited one first.

    Returns the sidecar filename if one was written. The sidecar extension is not
    .md, so vault-list/vault-view (both rglob '*.md') ignore it entirely.
    """
    dest = vault_dir / C.CLAUDE_MD
    sidecar = None
    if dest.is_file():
        pristine = C.render_template("research-topic-CLAUDE.md", {
            "<vault-title>": title_of(dest, vault_title),
            "<vault-slug>": slug,
            "<classifier>": classifier,
            "<YYYY-MM-DD>": today,
        })
        if dest.read_text(encoding="utf-8") != pristine:
            sidecar = "CLAUDE.md.pre-graduation"
            shutil.copy2(dest, vault_dir / sidecar)

    listing = "\n".join(f"- `{e}`" for e in unrepro) or "_(none)_"
    text = C.render_template("graduated-vault-CLAUDE.md", {
        "<vault-title>": vault_title,
        "<vault-name>": vault_name,
        "<classifier>": classifier,
        "<slug>": slug,
        "<YYYY-MM-DD>": today,
        "<unreproducible-list>": listing,
        "<layout-tree>": layout_tree(vault_dir, tool_owned, unrepro),
    })
    dest.write_text(text, encoding="utf-8")
    return sidecar


# ────────────────────────────────── main ─────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Graduate a tier-2 classified vault into a tier-1 vault.")
    p.add_argument("ref", help="Source vault: <classifier>/<slug> or a bare slug.")
    p.add_argument("--name", default=None,
                   help="Tier-1 name. '-vault' appended if absent. Default: <slug>-vault")
    p.add_argument("--domain", default=None,
                   help="Replaces the classifier value in overview.md's domain:.")
    p.add_argument("--dry-run", dest="dry_run", action="store_true",
                   help="Validate, audit, print the plan. Touch nothing.")
    p.add_argument("--force", action="store_true",
                   help="Override the audit refusal and the dirty-tree refusal.")
    p.add_argument("--git-dir", dest="git_dir", default=None)
    p.add_argument("--work-tree", dest="work_tree", default=None)
    p.add_argument("--no-git", dest="no_git", action="store_true",
                   help="Skip version control; move with shutil.")
    C.add_root_arg(p)
    return p


def _main(args) -> None:
    root = C.federation_root(args)
    C.require_root(root)
    today = datetime.date.today().isoformat()

    ref = C.resolve(root, args.ref)
    if ref is None:
        raise C.VaultError(
            f"vault not found: {args.ref} (under {root})",
            hint="Run /vault-x:list to see what exists.", code=C.E_NOTFOUND)

    # Idempotency: an already-graduated vault is a no-op, not an error.
    if ref.tier == C.TIER1:
        fm = C.load_frontmatter(ref.path / C.OVERVIEW)
        prior = fm.data.get("graduated_from")
        if prior:
            print(f"'{ref.rel}' already graduated from '{prior}' on "
                  f"{fm.data.get('graduated', 'an earlier date')}. Nothing to do.")
            return
        raise C.VaultError(
            f"'{ref.rel}' is already a tier-1 vault; nothing to graduate.",
            code=C.E_TIER)

    slug = ref.slug
    classifier = ref.classifier
    name = C.strip_vault_suffix(args.name.strip()) if args.name else slug
    C.validate_slug(name, what="tier-1 name")
    dest_ref = C.target_ref(root, name, None)

    if dest_ref.path.exists():
        raise C.VaultError(
            f"destination already exists: {dest_ref.rel}. Graduation never merges.",
            hint="Pass --name to graduate under a different name, or resolve the "
                 "existing vault first.",
            code=C.E_TIER)

    fm = C.load_frontmatter(ref.path / C.OVERVIEW)
    if fm.raw is None or fm.error:
        raise C.VaultError(
            f"{ref.rel}/overview.md has no usable frontmatter"
            + (f" ({fm.error})" if fm.error else "")
            + " — refusing to rewrite it.")
    vault_title = title_of(ref.path / C.CLAUDE_MD,
                           title_of(ref.path / C.OVERVIEW,
                                    slug.replace("-", " ").title()))

    tool_owned, unrepro = audit(ref.path)

    git_flags, worktree = resolve_git(root, ref.path, args)
    dirty: list = []
    if git_flags:
        dirty = check_clean(git_flags, worktree, ref.path)

    # ── the plan ──
    print(f"# Graduate {ref.label}\n")
    print(f"  source      {ref.rel}")
    print(f"  destination {dest_ref.rel}  (tier 1)")
    if git_flags:
        mech = ("ordinary repo" if git_flags[0] == "-C"
                else f"tracking repo {git_flags[1]}")
        print(f"  move        git mv via {mech}")
    else:
        print("  move        shutil.move  (no tracking repo detected)")
    print()
    print("## Reproducibility audit\n")
    print(f"  tool-owned ({len(tool_owned)}): "
          + (", ".join(tool_owned) if tool_owned else "none"))
    print(f"  unreproducible ({len(unrepro)}):")
    for e in unrepro:
        print(f"    - {e}")
    if not unrepro:
        print("    (none)")
    print()

    if not unrepro and not args.force:
        raise C.VaultError(
            f"nothing in '{ref.rel}' that a re-run of the '{classifier}/' tooling "
            f"could not reproduce.",
            hint="Graduation is one-way; don't spend it on a lab notebook that "
                 "merely got large. Re-run with --force only if you are certain.",
            code=C.E_TIER)

    if dirty and not args.force:
        raise C.VaultError(
            f"tracked changes under '{ref.rel}' — commit or stash first.\n  "
            + "\n  ".join(dirty[:10])
            + ("\n  ..." if len(dirty) > 10 else ""),
            hint="A clean tree is what makes the move recoverable. --force overrides.",
            code=C.E_GENERAL)

    print("## Frontmatter changes\n")
    print(f"  name: {name}")
    print(f"  domain: {args.domain or 'TODO  ← pass --domain to set this'}")
    print(f"  updated: {today}   graduated: {today}   graduated_from: {ref.rel}")
    print("  created: untouched")
    print()

    if args.dry_run:
        print("Dry run — nothing was written.")
        return

    # ── rewrite in place, THEN move (a failed move is one checkout away) ──
    changed = rewrite_overview(ref.path / C.OVERVIEW, name=name, domain=args.domain,
                               today=today, graduated_from=ref.rel)
    sidecar = write_tier1_claude(ref.path, vault_title=str(vault_title),
                                 vault_name=dest_ref.dirname, classifier=classifier,
                                 slug=slug, today=today,
                                 tool_owned=tool_owned, unrepro=unrepro)

    moved_with_git = False
    if git_flags:
        try:
            src_rel = ref.path.resolve().relative_to(worktree)
            dst_rel = dest_ref.path.resolve().relative_to(worktree)
            r = _git(git_flags, "mv", "--", str(src_rel), str(dst_rel))
            if r.returncode == 0:
                moved_with_git = True
            else:
                print(f"Warning: git mv failed ({r.stderr.strip()}); "
                      f"falling back to a plain move.", file=sys.stderr)
        except ValueError:
            pass
    if not moved_with_git:
        try:
            shutil.move(str(ref.path), str(dest_ref.path))
        except OSError as e:
            raise C.VaultError(
                f"move failed: {e}. The rewrites are still at '{ref.rel}'.",
                hint=f"Restore them with: git checkout -- {ref.rel}/",
            ) from e

    # The classifier dir is not itself tracked; drop it if it emptied out.
    classifier_dir = root / classifier
    try:
        if classifier_dir.is_dir() and not any(classifier_dir.iterdir()):
            classifier_dir.rmdir()
    except OSError:
        pass

    print(f"Moved {ref.rel} → {dest_ref.rel}")
    print()
    print("## Handoff\n")
    print(f"  path      {dest_ref.path}")
    print(f"  CLAUDE.md fill the `{LAYERS_OPEN}` block")
    print(f"  overview  fill the `{OVERVIEW_OPEN}` block")
    if not args.domain:
        print("  ⚠ domain: is TODO — set it to this vault's own subject, "
              "never the classifier")
    if sidecar:
        print(f"  ⚠ previous CLAUDE.md was hand-edited; saved as {sidecar} — reconcile it")
    print()
    print("  Unreproducible entries to describe:")
    for e in unrepro:
        print(f"    - {e}")
    print()
    if not moved_with_git:
        rel_home = ""
        try:
            rel_home = str(dest_ref.path.resolve().relative_to(Path.home()))
        except ValueError:
            rel_home = str(dest_ref.path)
        print("  Moved on disk, but NOT recorded in version control. Stage it with:")
        print(f"    henv add -A {rel_home}")
        print("  or:")
        print(f"    git --git-dir=$HOME/.home-env-git.git --work-tree=$HOME "
              f"add -A {rel_home}")
        print()
    print(f"  Next: /vault-x:view {dest_ref.rel}")


if __name__ == "__main__":
    C.run(build_parser(), _main)
