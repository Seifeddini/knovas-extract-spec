#!/usr/bin/env python3
"""
hash_fixtures.py — refresh MANIFEST.yaml hashes after adding/changing fixtures.

Scans `corpus/` and `corpus/adversarial/`, computes SHA-256 of every fixture
binary, and rewrites `MANIFEST.yaml::fixtures` and `MANIFEST.yaml::adversarial`
to match. Preserves any `tags`, `expected`, `provenance`, or `cve` fields
already present in the manifest.

Run after adding or replacing a fixture:

    python clients/extraction/spec/tooling/hash_fixtures.py

The script is idempotent — re-running on an up-to-date corpus is a no-op.

Dependencies: PyYAML >= 6.0.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    print("ERROR: missing PyYAML. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


SPEC_DIR = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SPEC_DIR / "MANIFEST.yaml"
CORPUS_DIR = SPEC_DIR / "corpus"
ADVERSARIAL_DIR = CORPUS_DIR / "adversarial"

# Files inside corpus/ that are NOT fixtures.
IGNORED_NAMES = frozenset({"README.md", ".gitkeep"})


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_fixture(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.name in IGNORED_NAMES:
        return False
    # .expected.json files are companions, not fixtures.
    if path.name.endswith(".expected.json"):
        return False
    return True


def scan_golden(existing: dict) -> dict:
    out: dict = {}
    for format_dir in sorted(CORPUS_DIR.iterdir()):
        if not format_dir.is_dir() or format_dir.name == "adversarial":
            continue
        for fixture_path in sorted(format_dir.iterdir()):
            if not is_fixture(fixture_path):
                continue
            rel_key = fixture_path.relative_to(CORPUS_DIR).as_posix()
            prior = existing.get(rel_key, {}) or {}
            entry = {
                "sha256": sha256_of(fixture_path),
                "size": fixture_path.stat().st_size,
            }
            # Preserve user-curated fields.
            if "tags" in prior:
                entry["tags"] = prior["tags"]
            if "tolerance_override" in prior:
                entry["tolerance_override"] = prior["tolerance_override"]
            out[rel_key] = entry
    return out


def scan_adversarial(existing: dict) -> dict:
    out: dict = {}
    if not ADVERSARIAL_DIR.is_dir():
        return out
    for format_dir in sorted(ADVERSARIAL_DIR.iterdir()):
        if not format_dir.is_dir():
            continue
        for fixture_path in sorted(format_dir.iterdir()):
            if not is_fixture(fixture_path):
                continue
            rel_key = fixture_path.relative_to(ADVERSARIAL_DIR).as_posix()
            prior = existing.get(rel_key, {}) or {}
            entry = {
                "sha256": sha256_of(fixture_path),
                "size": fixture_path.stat().st_size,
            }
            for k in ("expected", "provenance", "cve", "tags", "notes"):
                if k in prior:
                    entry[k] = prior[k]
            # If the user has not yet declared `expected`, leave a TODO marker
            # so validate_corpus.py fails loudly until they fill it in.
            entry.setdefault("expected", "TODO-set-expected-behavior")
            out[rel_key] = entry
    return out


def main() -> int:
    if not MANIFEST_PATH.is_file():
        print(f"ERROR: {MANIFEST_PATH} not found.", file=sys.stderr)
        return 2

    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}

    existing_fixtures = manifest.get("fixtures") or {}
    existing_adv = manifest.get("adversarial") or {}

    new_fixtures = scan_golden(existing_fixtures)
    new_adv = scan_adversarial(existing_adv)

    changed = (new_fixtures != existing_fixtures) or (new_adv != existing_adv)

    manifest["fixtures"] = new_fixtures
    manifest["adversarial"] = new_adv

    if not changed:
        print(
            f"OK: MANIFEST.yaml already up to date "
            f"({len(new_fixtures)} fixtures, {len(new_adv)} adversarial)."
        )
        return 0

    # Preserve top-level key order for diff stability.
    ordered_keys = [
        "spec_version",
        "corpus_version",
        "last_updated",
        "tolerances",
        "fixtures",
        "adversarial",
    ]
    # Keep any unknown keys at the end so we never silently drop user content.
    for k in list(manifest.keys()):
        if k not in ordered_keys:
            ordered_keys.append(k)
    ordered = {k: manifest[k] for k in ordered_keys if k in manifest}

    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            ordered,
            f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )

    print(
        f"UPDATED: MANIFEST.yaml now lists {len(new_fixtures)} fixture(s), "
        f"{len(new_adv)} adversarial fixture(s)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
