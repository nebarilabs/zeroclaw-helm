"""Deterministic structural invariants for the OKF bundle.

The machine-checkable half of a Karpathy-style lint pass — no LLM, no
graphify-out/ needed. Runs against the real bundle, so it belongs in CI
alongside okflint and covers what okflint only warns on (cross-links) plus
index/log drift that okflint cannot see. This is a generic, per-repo-adaptive
port; each repo's own `okf/okf-base.yaml` is the single enforcement source.

Design notes:
- The bundle root is resolved relative to this file. Sync distributes this
  module to each repo at `.github/tests/test_bundle_invariants.py`, so the
  repo root is two levels up.
- Repos with a flat `okf/concepts/*.md` layout (no per-type subdirectories)
  skip the index<->dir agreement checks automatically. Repos with no bundle
  at all are skipped entirely (they opt out by not providing okf-base.yaml).
- Cross-repo pointer liveness stays in the central hub (org-knowledge's
  check-pointers.py); only the hub knows the federation map.
- index<->dir agreement is enforced only where the bundling convention is a
  strict pointer table (projects -> overview.md, agents -> index/overview.md).
  Doc-table dirs (domains/, patterns/) intentionally mix prose links, nested
  subdirs, and ADRs, so they are not a 1:1 pointer map and are left to okflint.
"""

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OKF_DIR = REPO_ROOT / "okf"

# Root-level docs whose prose may cite live bundle sizes; the "counts rot"
# invariant guards them specifically (mirrors org-knowledge's original scope).
COUNT_CHECKED_DOCS = ["AGENTS.md", "README.md"]

# Names of backstop invariants that must never silently stop running.
# Guards against okflint-config regressions of the @v1 fan-out kind.
HARDCODED_COUNT_NOUNS = ["projects?", "repos?", "concepts?", "agents?", "domains?", "patterns?"]

# Bundle-prose count guard: a `<N> <noun>` is legal only on a line pinned to a
# re-derivation anchor (an ISO date or a sweep/swept reference), or when the
# number is a roadmap phase label ("Phase 1 agent"), or in log.md (append-only
# history, already dated by its `## YYYY-MM-DD` section headings).
COUNT_ANCHOR_RE = re.compile(r"\d{4}-\d{2}-\d{2}|\bsweep(?:s|ed|ing)?\b", re.IGNORECASE)
COUNT_PHASE_PREFIX_RE = re.compile(r"\bphase\s+$", re.IGNORECASE)
COUNT_SKIP_BASENAMES = {"log.md"}


def frontmatter_block(text: str) -> str:
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    return text[4:end] if end != -1 else ""


def parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[4:end]
    try:
        return yaml.safe_load(block) or {}
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        if mark is not None:
            raise AssertionError(
                f"{path}: invalid YAML in frontmatter (line {mark.line + 1}): "
                f"{exc.problem}" + (
                    f" — unquoted ':' in a scalar is the usual cause"
                    if "mapping values are not allowed" in (exc.problem or "")
                    else ""
                )
            ) from exc
        raise AssertionError(f"{path}: invalid YAML in frontmatter: {exc}") from exc


def _manifest() -> dict:
    with (OKF_DIR / "okf-base.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def reserved_names() -> set[str]:
    """Reserved filenames come from the manifest, not a hardcoded set."""
    reserved = _manifest().get("base", {}).get("reserved_files", {})
    return {v for v in reserved.values() if v}


def all_bundle_md():
    return sorted(p for p in OKF_DIR.rglob("*.md"))


def concept_files():
    """Non-reserved concept files, plus any reserved file that is itself a
    typed concept (single-pointer layouts use index.md as the Project/Agent
    pointer rather than a bare version carrier)."""
    reserved = reserved_names()
    files = []
    for p in all_bundle_md():
        if p.name not in reserved:
            files.append(p)
        elif _is_typed_pointer(p):
            files.append(p)
    return files


def _is_typed_pointer(path: Path) -> bool:
    fm = parse_frontmatter(path)
    if fm is None:
        return False
    try:
        types = _manifest()["profile"]["types"]
    except (KeyError, yaml.YAMLError):
        return False
    return fm.get("type") in types


def require_bundle():
    """Skip the whole module when the repo has no OKF bundle to lint."""
    if not (OKF_DIR / "okf-base.yaml").exists():
        pytest.skip("no okf/okf-base.yaml in this repo — nothing to validate")
    if not OKF_DIR.exists():
        pytest.skip("no okf/ directory in this repo — nothing to validate")


@pytest.fixture(scope="module", autouse=True)
def _bundle_guard():
    require_bundle()
    return True


@pytest.fixture(scope="module")
def profile_types():
    require_bundle()
    manifest = _manifest()
    return manifest["profile"]["types"]


# ------------------------------------------------------------- frontmatter

def test_every_concept_file_has_frontmatter():
    require_bundle()
    missing = [str(p) for p in concept_files() if parse_frontmatter(p) is None]
    assert not missing, f"concept files without valid frontmatter: {missing}"


def test_type_is_from_manifest_profile(profile_types):
    bad = []
    for p in concept_files():
        fm = parse_frontmatter(p)
        if fm.get("type") not in profile_types:
            bad.append((str(p), fm.get("type")))
    assert not bad, f"unknown/missing type: {bad}"


def test_required_fields_per_type_match_okf_base(profile_types):
    require_bundle()
    violations = []
    for p in concept_files():
        fm = parse_frontmatter(p)
        typ = fm.get("type")
        if typ not in profile_types:
            continue
        for field in profile_types[typ].get("required", []):
            value = fm.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                violations.append((str(p), typ, field))
    assert not violations, f"missing required frontmatter (file, type, field): {violations}"


def test_bundle_root_index_only_carries_okf_version(profile_types):
    """The manifest-reserved root index must exist and parse. Three valid
    layouts are accepted:
      1. Linear pointer: idx carries only `okf_version` == manifest version
      2. Rich landing: idx has no frontmatter and a concept tree exists
      3. Single-pointer: idx itself is a typed concept (e.g. a Project
         pointer for the repo) whose `type` is from the manifest profile
    """
    require_bundle()
    index = OKF_DIR / "index.md"
    if not index.exists():
        pytest.fail("manifest reserves okf/index.md but it is missing")
    fm = parse_frontmatter(index)
    if fm is None:
        if not (OKF_DIR / "concepts").is_dir():
            pytest.fail(
                "okf/index.md has no frontmatter and no concept dir expects a "
                "landing page — linear layouts must carry okf_version"
            )
        return
    manifest_version = _manifest().get("okf_version")
    if "okf_version" in fm:
        assert fm.get("okf_version") == manifest_version, (
            f"okf/index.md okf_version mismatch: frontmatter {fm.get('okf_version')!r} "
            f"!= manifest {manifest_version!r}"
        )
        return
    # single-pointer layout: index.md is itself a typed concept file
    assert fm.get("type") in profile_types, (
        f"okf/index.md frontmatter is neither okf_version nor a valid "
        f"profile type (got {fm.get('type')!r})"
    )


# -------------------------------------------------------------- cross-links

MD_LINK = re.compile(r"\]\(([^)\s]+)\)")


def iter_links():
    for p in all_bundle_md():
        for m in MD_LINK.finditer(p.read_text(encoding="utf-8")):
            yield p, m.group(1)


def test_bundle_relative_md_links_resolve():
    require_bundle()
    broken = []
    for path, href in iter_links():
        if not href.startswith("/"):
            continue
        target = re.sub(r"#.*$", "", href)
        if not target.endswith(".md"):
            continue
        rel = target.lstrip("/")
        # accept both bundle-relative (/concepts/x.md) and bundle-qualified
        # (/okf/concepts/x.md) link styles
        candidates = [OKF_DIR / rel]
        if rel.startswith("okf/"):
            candidates.append(OKF_DIR / rel[len("okf/"):])
        if not any(c.exists() for c in candidates):
            broken.append((str(path), href))
    assert not broken, f"broken bundle-relative links: {broken}"


def test_no_relative_md_links_in_bundle():
    """Convention: bundle-relative links survive moves; `../` links to
    repo-root docs and bare links don't survive. Allow `../X.md` only when X
    exists at the repo root (a documented cross-layout link); flag everything
    else — a `../` target that does not resolve is real drift."""
    require_bundle()
    offenders = []
    for path, href in iter_links():
        if href.startswith(("http://", "https://", "mailto:", "/", "#")):
            continue
        if href.startswith("../"):
            target = re.sub(r"#.*$", "", href.lstrip("./"))
            if not (REPO_ROOT / target).exists():
                offenders.append((str(path), href))
        elif href.endswith(".md"):
            offenders.append((str(path), href))
    assert not offenders, (
        "bundle links must be bundle-relative (/path.md) or repo-root ../ links "
        f"that resolve; offenders: {offenders}"
    )


# -------------------------------------------- index <-> files (adaptive)

def _subdir_pointers(subdir: Path):
    """Direct child dirs that represent pointers (skip _ prefixed templates)."""
    if not subdir.is_dir():
        return set()
    return {p.name for p in subdir.iterdir() if p.is_dir() and not p.name.startswith("_")}


def _index_linked_names(index_file: Path, pattern: str):
    if not index_file.exists():
        return set()
    text = index_file.read_text(encoding="utf-8")
    return set(re.findall(pattern, text))


@pytest.mark.parametrize("subdir,entry_re", [
    ("projects", r"\(/(?:okf/)?projects/([^/]+)/overview\.md\)"),
    # agents bundles may be index.md placeholders OR overview.md when populated
    ("agents", r"\(/(?:okf/)?agents/([^/]+)/(?:index|overview)\.md\)"),
])
def test_subdir_dirs_and_index_agree(subdir, entry_re):
    """Run only for subdirectories that exist in this repo's layout."""
    require_bundle()
    sub = OKF_DIR / subdir
    if not sub.is_dir():
        pytest.skip(f"no okf/{subdir}/ layout in this repo")
    index_file = sub / "index.md"
    if not index_file.exists():
        pytest.skip(f"no okf/{subdir}/index.md in this repo")
    linked = _index_linked_names(index_file, entry_re)
    dirs = _subdir_pointers(sub)
    assert linked == dirs, (
        f"okf/{subdir}: index-only: {linked - dirs}, file-only: {dirs - linked}"
    )


def test_flat_concept_files_have_no_generated_count_prose():
    """'Counts are values' — prose in root landing docs must not hardcode
    bundle sizes that drift when a pointer is added."""
    require_bundle()
    offenders = []
    count_re = re.compile(
        r"(?<![\d-])\b(\d+)\s+(?:" + "|".join(HARDCODED_COUNT_NOUNS) + r")\b",
        re.IGNORECASE,
    )
    for name in COUNT_CHECKED_DOCS:
        doc = REPO_ROOT / name
        if not doc.exists():
            continue
        text = doc.read_text(encoding="utf-8")
        for m in count_re.finditer(text):
            offenders.append((name, m.group(0)))
    assert not offenders, (
        f"hardcoded bundle counts in {COUNT_CHECKED_DOCS} (drift on next "
        f"pointer added): {offenders}"
    )


def test_bundle_prose_has_no_undated_hardcoded_counts():
    """'Counts are values' (AGENTS.md) extended from root landing docs into
    the bundle itself: fleet sizes written in prose silently drift once a
    pointer is added or the deployment scales. Legal only with a re-derivation
    anchor on the same line (ISO date / sweep reference), as a roadmap phase
    label, or in log.md (append-only history dated by section headings).
    Found live drift during the 2026-09-07 runner migration review: the same
    fleet was cited as '13 agents', '7 agents', '16 repos', '18 repos' and
    '31 repos' across bundles — all undated."""
    require_bundle()
    count_re = re.compile(
        r"(?<![\d-])\b(\d+)\s+(?:" + "|".join(HARDCODED_COUNT_NOUNS) + r")\b",
        re.IGNORECASE,
    )
    offenders = []
    for path in all_bundle_md():
        if path.name in COUNT_SKIP_BASENAMES:
            continue
        rel = str(path.relative_to(REPO_ROOT))
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
        ):
            for m in count_re.finditer(line):
                if COUNT_ANCHOR_RE.search(line) or COUNT_PHASE_PREFIX_RE.search(
                    line[: m.start()]
                ):
                    continue
                offenders.append((rel, lineno, m.group(0)))
    assert not offenders, (
        "undated hardcoded counts in bundle prose — add a date/sweep anchor, "
        "rephrase to 'every synced ...', or state it as a Phase label: "
        f"{offenders}"
    )


def test_stale_after_is_plain_date_string():
    """okflint S204: `stale_after: 2026-12-06T00:00:00Z` (unquoted ISO) is parsed
    by YAML as a datetime, not the expected YYYY-MM-DD string. Regex over raw
    frontmatter lines on purpose — PyYAML coercion is the exact trap."""
    require_bundle()
    offenders = []
    for path in all_bundle_md():
        fm = frontmatter_block(path.read_text(encoding="utf-8"))
        for line in fm.splitlines():
            if line.strip().startswith("stale_after:") and not re.match(
                r'^stale_after:\s*"\d{4}-\d{2}-\d{2}"\s*$', line.strip()
            ):
                offenders.append((str(path), line.strip()))
    assert not offenders, f"stale_after must be a quoted YYYY-MM-DD string: {offenders}"
    # complement the raw-line regex (bypassable via flow mappings / spacing):
    # whatever the parser found, it must be a plain date string, not a datetime
    for path in all_bundle_md():
        fm = parse_frontmatter(path) or {}
        value = fm.get("stale_after")
        if value is not None:
            assert isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value), (
                f"{path}: stale_after parsed as {type(value).__name__} ({value!r}), "
                "expected 'YYYY-MM-DD'"
            )


# --------------------------------------------------------------------- log

def test_log_entries_use_greppable_date_headings():
    require_bundle()
    log_file = OKF_DIR / "log.md"
    if not log_file.exists():
        pytest.skip("no okf/log.md in this repo")
    bad = [
        line for line in log_file.read_text(encoding="utf-8").splitlines()
        if line.startswith("## ") and not re.match(r"^## \d{4}-\d{2}-\d{2}$", line)
    ]
    assert not bad, f"log.md headings must be '## YYYY-MM-DD': {bad}"
