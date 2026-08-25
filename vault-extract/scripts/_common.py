"""Shared core for the vault-x scripts.

Owns the two-tier federation standard:

    ~/knowledge-vaults/
    ├── <name>-vault/            TIER 1 — graduated, hand-maintained
    └── <classifier>/<slug>/     TIER 2 — machine-produced

A `-vault` suffix means tier 1. Membership in a classifier directory means tier 2,
and the slug carries no suffix. Never both.

This module NEVER calls sys.exit() and never writes to stderr. It raises VaultError.
Entry-point scripts call `run(parser, main)`, which renders the error and picks the
exit code. That keeps resolution composable: a caller can resolve a target and then
decide what to do about ambiguity, rather than being killed mid-library.

Import from a sibling script with:

    _HERE = str(Path(__file__).resolve().parent)
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import _common as C
"""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

# ───────────────────────────────── constants ─────────────────────────────────

VAULT_SUFFIX = "-vault"
DEFAULT_CLASSIFIER = "research"

TIER1 = 1
TIER2 = 2

EXCLUDED_DIRS = {".obsidian", ".git", ".trash", ".DS_Store"}
META_FILES = {"overview.md", "CLAUDE.md"}
OVERVIEW = "overview.md"
CLAUDE_MD = "CLAUDE.md"

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
DEFAULT_ROOT = Path.home() / "knowledge-vaults"

SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Frontmatter delimiters must each be a complete line. The old
# text.split("---", 2) truncated at the first "---" appearing inside a value,
# and the live overview.md files use `purpose: |` block scalars.
FM_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)

# ─────────────────────────────────── errors ──────────────────────────────────

E_GENERAL = 1
# 2 is reserved: argparse exits 2 on usage errors.
E_NOTFOUND = 3
E_AMBIGUOUS = 4
E_TIER = 5


class VaultError(Exception):
    """A user-facing failure. `hint` carries the actionable remedy."""

    def __init__(self, msg: str, *, hint: str | None = None, code: int = E_GENERAL):
        super().__init__(msg)
        self.hint = hint
        self.code = code


# ───────────────────────────────── cli helpers ───────────────────────────────


def add_root_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root", type=str, default=None,
        help="Federation root path. Default: ~/knowledge-vaults/",
    )


def federation_root(args) -> Path:
    """Resolved absolute federation root.

    .resolve() is load-bearing: every containment check (is_relative_to) and every
    relative_to() call downstream is only sound against a resolved root, or a
    symlinked path silently fails containment.
    """
    raw = getattr(args, "root", None)
    base = Path(raw).expanduser() if raw else DEFAULT_ROOT
    return base.resolve()


def require_root(root: Path) -> None:
    if not root.is_dir():
        raise VaultError(
            f"federation root does not exist: {root}",
            hint="Run /vault-x:init first.",
            code=E_NOTFOUND,
        )


def run(parser: argparse.ArgumentParser, fn) -> None:
    """Uniform entrypoint. Every script's `main` becomes `run(parser, _main)`."""
    args = parser.parse_args()
    try:
        fn(args)
    except VaultError as e:
        print(f"Error: {e}", file=sys.stderr)
        if e.hint:
            print(f"Hint: {e.hint}", file=sys.stderr)
        sys.exit(e.code)
    except BrokenPipeError:
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)


# ──────────────────────────────── text helpers ───────────────────────────────


def slugify(text: str, *, limit: int = 60, fallback: str = "") -> str:
    """kebab-case ASCII slug.

    NFKD-decompose before dropping non-ASCII, so 'naive' survives as 'naive'
    rather than 'nave' (raw encode) or 'na-ve' (substitute-first). No-op on
    ASCII input, so every existing on-disk slug is unchanged.

    `fallback` is explicit and defaults to empty: a slug that silently became
    some hardcoded word because the input was all emoji is a bug, not a default.
    """
    s = unicodedata.normalize("NFKD", text.strip().lower())
    s = s.encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > limit:
        s = s[:limit].rsplit("-", 1)[0].strip("-")
    return s or fallback


def strip_vault_suffix(name: str) -> str:
    """Pure string op. No validation, no I/O."""
    name = name.strip()
    return name[: -len(VAULT_SUFFIX)] if name.endswith(VAULT_SUFFIX) else name


def host_of(url: str) -> str:
    try:
        h = urlparse(url).hostname or "source"
    except ValueError:
        h = "source"
    return h.replace("www.", "").strip(".") or "source"


def source_slug(url: str) -> str:
    """Host + path slug, so two pages on one host don't collide."""
    try:
        parts = urlparse(url)
        host = (parts.hostname or "source").replace("www.", "").strip(".")
        path = parts.path or ""
    except ValueError:
        host, path = "source", ""
    return slugify(f"{host} {path}", fallback="source")


def short_title(text: str, limit: int = 72) -> str:
    s = " ".join(text.strip().split())
    for sep in (". ", "? ", "! "):
        if sep in s:
            s = s.split(sep, 1)[0]
            break
    s = s.rstrip(".?!")
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


def render_template(name: str, subs: dict[str, str], *, indent_keys: tuple = ()) -> str:
    """Read templates/<name> and substitute placeholder tokens.

    Tokens listed in `indent_keys` (e.g. '  <purpose>') are replaced with their
    value indented two spaces, matching the `purpose: |` block-scalar shape.
    """
    path = TEMPLATES_DIR / name
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise VaultError(f"template not found: {path} ({e})") from e
    for token, value in subs.items():
        if token in indent_keys:
            text = text.replace(token, textwrap.indent(str(value).strip(), "  "))
        else:
            text = text.replace(token, str(value))
    return text


# ───────────────────────────────── validation ────────────────────────────────


def validate_slug(slug: str, *, what: str = "vault name") -> str:
    """Raise unless `slug` is a legal vault/classifier directory name.

    The VAULT_SUFFIX rejection here is half of the 'never both' rule. At tier 1
    the suffix is appended by target_ref, so an input already carrying it would
    double ('personal-tax-vault' -> 'personal-tax-vault-vault'). At tier 2 the
    suffix is forbidden outright.
    """
    if not slug:
        raise VaultError(f"{what} cannot be empty.")
    if not SLUG_RE.match(slug):
        raise VaultError(
            f"{what} must be alphanumeric with . _ - only: {slug!r}",
            hint="No whitespace, no path separators, no leading dot.",
        )
    if slug.endswith(VAULT_SUFFIX):
        raise VaultError(
            f"{what} must not carry the {VAULT_SUFFIX!r} suffix here.",
            hint=f"Pass the bare name, e.g. {strip_vault_suffix(slug)!r}.",
            code=E_TIER,
        )
    if slug in EXCLUDED_DIRS:
        raise VaultError(f"{what} is a reserved directory name: {slug!r}")
    return slug


def validate_classifier(name: str) -> str:
    return validate_slug(name, what="classifier")


# ──────────────────────────────── frontmatter ────────────────────────────────

_YAML = None


def _yaml():
    """Lazy yaml import.

    Lazy rather than import-time so vault-init and vault-create, which parse no
    YAML, don't acquire a hard pyyaml dependency merely by importing _common.
    """
    global _YAML
    if _YAML is None:
        try:
            import yaml  # noqa: PLC0415
        except ImportError as e:
            raise VaultError(
                "pyyaml not found. Install: pip install pyyaml"
            ) from e
        _YAML = yaml
    return _YAML


@dataclass(frozen=True)
class Frontmatter:
    """Lossless frontmatter read.

    Carries every distinction so each caller can ignore what it doesn't need:
    vault-list REPORTS three failure modes, vault-view IGNORES all of them.

    raw   — YAML text between the delimiters; None means no block at all.
    data  — parsed mapping; {} if absent OR invalid OR not-a-mapping.
    body  — everything after the closing delimiter.
    error — pre-rendered reason data is {} despite raw being present.
    """

    raw: str | None
    data: dict
    body: str
    error: str | None


def parse_frontmatter(text: str) -> Frontmatter:
    m = FM_RE.match(text)
    if not m:
        return Frontmatter(None, {}, text, None)
    raw = m.group(1)
    body = text[m.end():]
    try:
        data = _yaml().safe_load(raw)
    except Exception as e:  # yaml.YAMLError, but keep yaml out of caller scope
        return Frontmatter(raw, {}, body, f"malformed YAML: {e}")
    if data is None:
        return Frontmatter(raw, {}, body, None)
    if not isinstance(data, dict):
        return Frontmatter(raw, {}, body, "frontmatter is not a mapping")
    return Frontmatter(raw, data, body, None)


def load_frontmatter(path: Path) -> Frontmatter:
    try:
        return parse_frontmatter(path.read_text(encoding="utf-8"))
    except OSError:
        return Frontmatter(None, {}, "", None)


def dump_frontmatter(fields: dict) -> str:
    y = _yaml().safe_dump(
        fields, sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    return f"---\n{y}---\n"


def bump_updated(vault_dir: Path, today: str) -> bool:
    """Set overview.md's `updated:` to today, INSIDE the frontmatter block only.

    Returns False if there is no overview.md or no frontmatter block, so callers
    can warn instead of silently doing nothing.

    Fixes over the previous copies: scoped to the block (a body line starting
    'updated: ' is no longer hijacked); `\\s*:` matches 'updated:2026-01-01';
    the for/else structure makes double-insertion structurally impossible; and
    the key is appended when neither `updated:` nor `created:` exists.
    """
    p = vault_dir / OVERVIEW
    if not p.is_file():
        return False
    try:
        text = p.read_text(encoding="utf-8")
    except OSError:
        return False
    m = FM_RE.match(text)
    if not m:
        return False

    lines = m.group(1).split("\n")
    rest = text[m.end():]

    for i, ln in enumerate(lines):
        if re.match(r"^updated\s*:", ln):
            lines[i] = f"updated: {today}"
            break
    else:
        for i, ln in enumerate(lines):
            if re.match(r"^created\s*:", ln):
                lines.insert(i + 1, f"updated: {today}")
                break
        else:
            lines.append(f"updated: {today}")

    p.write_text("---\n" + "\n".join(lines) + "\n---\n" + rest, encoding="utf-8")
    return True


def set_frontmatter_key(path: Path, key: str, value: str, *, after: str | None = None) -> bool:
    """Set or insert one scalar key inside the frontmatter block. Line-level, so
    unrelated formatting (block scalars, comments, key order) survives byte-identical."""
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return False
    lines = m.group(1).split("\n")
    rest = text[m.end():]
    pat = re.compile(rf"^{re.escape(key)}\s*:")
    for i, ln in enumerate(lines):
        if pat.match(ln):
            lines[i] = f"{key}: {value}"
            break
    else:
        if after:
            apat = re.compile(rf"^{re.escape(after)}\s*:")
            for i, ln in enumerate(lines):
                if apat.match(ln):
                    lines.insert(i + 1, f"{key}: {value}")
                    break
            else:
                lines.append(f"{key}: {value}")
        else:
            lines.append(f"{key}: {value}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + rest, encoding="utf-8")
    return True


# ────────────────────────────────── model ────────────────────────────────────


@dataclass(frozen=True)
class VaultRef:
    """A vault that exists, or a well-formed target for one.

    Position IS tier. `rel` is computed from (tier, classifier, slug) and never
    from path.relative_to(root), so it cannot raise regardless of user input.
    """

    tier: int
    slug: str                 # never carries VAULT_SUFFIX
    classifier: str | None    # None at tier 1
    path: Path
    root: Path

    @property
    def dirname(self) -> str:
        return f"{self.slug}{VAULT_SUFFIX}" if self.tier == TIER1 else self.slug

    @property
    def rel(self) -> str:
        if self.tier == TIER1:
            return self.dirname
        return f"{self.classifier}/{self.dirname}"

    @property
    def label(self) -> str:
        return f"{self.rel} (tier {self.tier})"

    @property
    def sort_key(self):
        return (self.tier, self.classifier or "", self.slug)

    def exists(self) -> bool:
        return self.path.is_dir()

    def has_overview(self) -> bool:
        return (self.path / OVERVIEW).is_file()


@dataclass(frozen=True)
class RefIntent:
    """A parsed user string. No filesystem contact."""

    kind: str                 # "tier1" | "tier2" | "bare"
    slug: str
    classifier: str | None    # set iff kind == "tier2"
    raw: str


@dataclass(frozen=True)
class Anomaly:
    rel: str
    reason: str


@dataclass(frozen=True)
class Discovery:
    vaults: list          # list[VaultRef], sorted by sort_key
    anomalies: list       # list[Anomaly]


# ───────────────────────────────── resolver ──────────────────────────────────


def _relativize(root: Path, raw: str) -> str:
    """Turn an absolute path inside the root into a federation-relative ref.

    Replaces the silent escape in the old resolver, where `root / "/abs"` returned
    "/abs" and the subsequent relative_to() raised an uncaught ValueError.
    """
    s = raw.strip()
    if not (s.startswith("/") or s.startswith("~")):
        return s
    p = Path(s).expanduser().resolve()
    # Resolve the root too: callers normally pass a resolved root via
    # federation_root(), but on macOS an unresolved /var/... root would fail
    # containment against a resolved /private/var/... path.
    root = root.resolve()
    if p == root:
        raise VaultError(
            f"'{raw}' is the federation root, not a vault.",
            hint="Run /vault-x:list to see the vaults it contains.",
        )
    try:
        rel = p.relative_to(root)
    except ValueError:
        raise VaultError(
            f"'{raw}' is outside the federation root ({root}).",
            hint="Pass a reference relative to the root, or set --root.",
        ) from None
    return str(rel)


def parse_ref(raw: str) -> RefIntent:
    """Classify a user reference. Pure, total, no I/O."""
    s = raw.strip().rstrip("/")
    if not s:
        raise VaultError("vault reference cannot be empty.")

    if s.startswith("/") or s.startswith("~") or "\\" in s:
        raise VaultError(
            f"'{raw}' is not a federation-relative reference.",
            hint="References are relative to the federation root, e.g. "
                 "'research/local-llms' or 'personal-tax-vault'.",
        )
    if any(ch.isspace() for ch in s):
        raise VaultError(f"vault reference must not contain whitespace: {raw!r}")

    segs = s.split("/")
    if any(seg in ("", ".", "..") for seg in segs):
        raise VaultError(f"'{raw}' contains an empty or traversal path segment.")

    if len(segs) == 1:
        seg = segs[0]
        if seg.endswith(VAULT_SUFFIX):
            slug = strip_vault_suffix(seg)
            validate_slug(slug)
            return RefIntent("tier1", slug, None, raw)
        validate_slug(seg)
        return RefIntent("bare", seg, None, raw)

    if len(segs) == 2:
        c, sl = segs
        if c.endswith(VAULT_SUFFIX):
            raise VaultError(
                f"'{raw}' points INSIDE the tier-1 vault '{c}'.",
                hint=f"A vault reference stops at the vault directory: '{c}'.",
            )
        if sl.endswith(VAULT_SUFFIX):
            raise VaultError(
                f"'{raw}' violates the two-tier standard: a vault inside the '{c}' "
                f"classifier must not carry the '{VAULT_SUFFIX}' suffix — the "
                f"classifier already names its kind.",
                hint=f"Use '{c}/{strip_vault_suffix(sl)}' (tier 2) or '{sl}' (tier 1). "
                     f"Never both.",
                code=E_TIER,
            )
        validate_classifier(c)
        validate_slug(sl)
        return RefIntent("tier2", sl, c, raw)

    head = "/".join(segs[:2])
    raise VaultError(
        f"'{raw}' is not a vault — vaults live at '<name>{VAULT_SUFFIX}/' or "
        f"'<classifier>/<slug>/', nothing deeper.",
        hint=f"Did you mean the vault '{head}'? Run folders, 'sources/' and "
             f"'records/' are vault CONTENTS, not vaults.",
    )


def _confirm(ref: VaultRef, require_overview: bool) -> VaultRef | None:
    if not ref.path.is_dir():
        return None
    if require_overview and not ref.has_overview():
        return None
    return ref


def resolve(root: Path, raw: str, *,
            require_overview: bool = True,
            index: list | None = None) -> VaultRef | None:
    """Resolve a user reference to a vault on disk.

    Returns None ONLY for 'not found'. Raises VaultError for malformed refs, tier
    violations, and cross-tier ambiguity.

    A bare slug goes straight to federation-wide discovery — there is deliberately
    no tier-1 fallback branch. The old resolver's legacy `<name>-vault` fallback
    short-circuited before the ambiguity guard, so a slug matching both tiers
    silently returned tier 1 and the guard never fired.

    `require_overview` applies to explicit refs only; discovery already surfaces
    overview-bearing directories exclusively. For an occupancy check on a path,
    pass an explicit ref or use target_ref(...).path.exists().
    """
    intent = parse_ref(_relativize(root, raw))

    if intent.kind == "tier1":
        return _confirm(
            VaultRef(TIER1, intent.slug, None,
                     root / f"{intent.slug}{VAULT_SUFFIX}", root),
            require_overview,
        )

    if intent.kind == "tier2":
        return _confirm(
            VaultRef(TIER2, intent.slug, intent.classifier,
                     root / intent.classifier / intent.slug, root),
            require_overview,
        )

    if index is None:
        index = discover(root).vaults
    matches = [v for v in index if v.slug == intent.slug]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    matches.sort(key=lambda v: v.sort_key)
    raise VaultError(
        f"'{raw}' is ambiguous — it matches {len(matches)} vaults across tiers: "
        + ", ".join(m.label for m in matches) + ".",
        hint=f"Pass the full reference, e.g. '{matches[0].rel}'. If one of these is "
             f"a leftover from a graduation, remove it — graduation is a move "
             f"(git mv), not a copy; a topic must exist at exactly one tier.",
        code=E_AMBIGUOUS,
    )


def target_ref(root: Path, slug: str, classifier: str | None) -> VaultRef:
    """The ONE place root/<classifier>/<slug> vs root/<slug>-vault is decided."""
    validate_slug(slug)
    if classifier is None:
        return VaultRef(TIER1, slug, None, root / f"{slug}{VAULT_SUFFIX}", root)
    validate_classifier(classifier)
    return VaultRef(TIER2, slug, classifier, root / classifier / slug, root)


def target_path(root: Path, slug: str, classifier: str | None) -> Path:
    return target_ref(root, slug, classifier).path


def _skip_dir(p: Path) -> bool:
    return (not p.is_dir()) or p.name.startswith(".") or p.name in EXCLUDED_DIRS


def discover(root: Path) -> Discovery:
    """Enumerate vaults with two bounded iterdir() levels.

    Structural, not rglob: a vault exists at exactly two positions, so tier and
    classifier are read off the position rather than inferred by splitting an
    unbounded walk. A tier-1 vault is never descended into, so an overview.md in
    personal-tax-vault/records/ is content, not a phantom vault at no tier.

    Malformed placements surface as anomalies rather than being silently invisible,
    which is what makes the standard self-policing in /vault-x:list.
    """
    vaults: list = []
    anomalies: list = []

    if not root.is_dir():
        return Discovery(vaults, anomalies)

    for d1 in sorted(root.iterdir(), key=lambda p: p.name):
        if _skip_dir(d1):
            continue

        has_ov = (d1 / OVERVIEW).is_file()

        if d1.name.endswith(VAULT_SUFFIX):
            if has_ov:
                vaults.append(
                    VaultRef(TIER1, strip_vault_suffix(d1.name), None, d1, root)
                )
            else:
                anomalies.append(Anomaly(
                    d1.name,
                    f"'{VAULT_SUFFIX}' directory with no {OVERVIEW}",
                ))
            continue  # never descend into a tier-1 vault

        if has_ov:
            anomalies.append(Anomaly(
                d1.name,
                f"vault at the federation root without the '{VAULT_SUFFIX}' suffix — "
                f"rename to '{d1.name}{VAULT_SUFFIX}' (tier 1) or move it under a "
                f"classifier (tier 2)",
            ))
            continue

        for d2 in sorted(d1.iterdir(), key=lambda p: p.name):
            if _skip_dir(d2):
                continue
            if not (d2 / OVERVIEW).is_file():
                continue
            if d2.name.endswith(VAULT_SUFFIX):
                anomalies.append(Anomaly(
                    f"{d1.name}/{d2.name}",
                    f"tier-2 vault carrying the '{VAULT_SUFFIX}' suffix — never both; "
                    f"rename to '{d1.name}/{strip_vault_suffix(d2.name)}'",
                ))
                continue
            vaults.append(VaultRef(TIER2, d2.name, d1.name, d2, root))

    vaults.sort(key=lambda v: v.sort_key)
    return Discovery(vaults, anomalies)


# ─────────────────────────────── write policy ────────────────────────────────


@dataclass(frozen=True)
class WriteTarget:
    ref: VaultRef
    exists: bool        # a scaffolded vault is already there
    must_create: bool   # caller should scaffold (implies not exists)


def resolve_write_target(root: Path, raw: str, *,
                         default_classifier: str = DEFAULT_CLASSIFIER,
                         create: bool = False,
                         allow_new_classifier: bool = False) -> WriteTarget:
    """Where should this write land, and may it be created?

    Unifies research-scaffold's ensure_topic_vault and research-source's
    fail-closed check — the same decision, one bit different (`create`).

    Tier-1 targets are written to implicitly; the always-confirm step in the
    command layer is the gate. What is NOT implicit is creation: tooling may
    materialise <classifier>/<slug>/ but never <name>-vault/.
    """
    index = discover(root).vaults
    intent = parse_ref(_relativize(root, raw))
    found = resolve(root, raw, require_overview=True, index=index)

    if found is not None:
        return WriteTarget(found, exists=True, must_create=False)

    # Not found at the requested position. Does the topic live somewhere else?
    cross = [v for v in index if v.slug == intent.slug]
    if cross:
        other = sorted(cross, key=lambda v: v.sort_key)[0]
        would = target_ref(root, intent.slug,
                           None if intent.kind == "tier1"
                           else (intent.classifier or default_classifier))
        raise VaultError(
            f"'{other.rel}' already holds the topic '{intent.slug}' at tier "
            f"{other.tier}; nothing exists at '{would.rel}'. Creating it would fork "
            f"the topic into a duplicate vault at a second tier.",
            hint=f"Write into the existing vault instead: --vault {other.rel}. "
                 f"Graduation is one-way (git mv) — there is no second copy by "
                 f"design. If the vault really should be recreated at "
                 f"'{would.rel}', remove or rename '{other.rel}' first.",
            code=E_TIER,
        )

    if not create:
        raise VaultError(
            f"vault not found: '{raw}' (under {root}).",
            hint="Run /vault-x:research into it first, or check /vault-x:list.",
            code=E_NOTFOUND,
        )

    if intent.kind == "tier1":
        raise VaultError(
            f"will not create the tier-1 vault '{intent.slug}{VAULT_SUFFIX}'. Tier 1 "
            f"is reached by /vault-x:create, or by graduating a tier-2 vault.",
            hint=f"To start a new research topic: "
                 f"--vault {default_classifier}/{intent.slug}",
            code=E_TIER,
        )

    classifier = intent.classifier or default_classifier
    validate_classifier(classifier)
    if (classifier != DEFAULT_CLASSIFIER
            and not (root / classifier).is_dir()
            and not allow_new_classifier):
        raise VaultError(
            f"classifier '{classifier}/' does not exist. Adding a classifier means "
            f"adding a new KIND of machine-produced vault with its own generator — "
            f"not a topic category.",
            hint="If that is really what you mean, pass --allow-new-classifier. "
                 "Otherwise check the spelling against /vault-x:list.",
            code=E_TIER,
        )

    return WriteTarget(target_ref(root, intent.slug, classifier),
                       exists=False, must_create=True)


def scaffold_tier2_vault(ref: VaultRef, *, vault_title: str, purpose: str,
                         today: str) -> list:
    """Create only what is missing. NEVER overwrites an existing file.

    Gap-filling rather than all-or-nothing: a crashed first run used to leave a
    bare directory that every later run early-returned on, so the vault stayed
    permanently without overview.md and invisible to every tool.
    """
    if ref.tier != TIER2:
        raise VaultError(
            f"refusing to scaffold '{ref.rel}': only tier-2 vaults are "
            f"machine-created.",
            code=E_TIER,
        )

    ref.path.mkdir(parents=True, exist_ok=True)
    (ref.path / ".obsidian").mkdir(exist_ok=True)
    written: list = []

    if not (ref.path / OVERVIEW).is_file():
        text = render_template(
            "research-topic-overview.md",
            {
                "<vault-slug>": ref.slug,
                "<vault-title>": vault_title,
                "<classifier>": ref.classifier or DEFAULT_CLASSIFIER,
                "  <purpose>": purpose,
                "<YYYY-MM-DD>": today,
            },
            indent_keys=("  <purpose>",),
        )
        (ref.path / OVERVIEW).write_text(text, encoding="utf-8")
        written.append(OVERVIEW)

    if not (ref.path / CLAUDE_MD).is_file():
        text = render_template(
            "research-topic-CLAUDE.md",
            {
                "<vault-slug>": ref.slug,
                "<vault-title>": vault_title,
                "<classifier>": ref.classifier or DEFAULT_CLASSIFIER,
                "<YYYY-MM-DD>": today,
            },
        )
        (ref.path / CLAUDE_MD).write_text(text, encoding="utf-8")
        written.append(CLAUDE_MD)

    return written


# ────────────────────────────────── content ──────────────────────────────────


def content_files(vault_dir: Path) -> list:
    """Sorted .md files under vault_dir, excluding META_FILES and EXCLUDED_DIRS.

    The exclusion test runs on parts RELATIVE to the vault: the previous copies
    tested absolute path parts, so a federation placed under any directory named
    '.git' or '.trash' silently reported zero files everywhere.
    """
    out: list = []
    for p in sorted(vault_dir.rglob("*.md")):
        if p.name in META_FILES:
            continue
        try:
            rel_parts = p.relative_to(vault_dir).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in rel_parts):
            continue
        out.append(p)
    return out
