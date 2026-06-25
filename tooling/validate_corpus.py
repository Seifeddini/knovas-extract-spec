#!/usr/bin/env python3
"""
validate_corpus.py — spec/corpus integrity check.

Runs on every PR touching `clients/extraction/spec/` (and locally by maintainers).
Verifies:

1. `schema.json` is itself a valid JSON Schema.
2. Every `*.expected.json` under `corpus/` validates against `schema.json`.
3. Every binary fixture under `corpus/<format>/` has a sibling `.expected.json`
   AND an entry in `MANIFEST.yaml::fixtures` (or `MANIFEST.yaml::adversarial`)
   with a matching SHA-256.
4. No orphaned `MANIFEST.yaml` entries (entry exists but file does not).
5. Adversarial fixtures declare an `expected` behavior (error class or warning).

Exit codes:
    0 — corpus is valid.
    1 — one or more validation failures (details printed to stderr).
    2 — unexpected error (missing dependency, IO failure, …).

Dependencies (stdlib + 2 PyPI):
    - jsonschema >= 4.0
    - PyYAML >= 6.0
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml  # type: ignore[import-not-found]
    from jsonschema import Draft202012Validator  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover
    print(
        f"ERROR: missing dependency ({exc.name}). "
        "Install with: pip install pyyaml jsonschema",
        file=sys.stderr,
    )
    sys.exit(2)


SPEC_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SPEC_DIR / "schema.json"
MANIFEST_PATH = SPEC_DIR / "MANIFEST.yaml"
CORPUS_DIR = SPEC_DIR / "corpus"

# Adversarial fixtures must declare one of these as their `expected` behavior.
ALLOWED_ADVERSARIAL_EXPECTED = frozenset(
    {
        "ResourceExhaustedError",
        "CorruptDocumentError",
        "EncryptedDocumentError",
        "UnsupportedFormatError",
        "DependencyMissingError",
        "warning",
        "sanitized",
    }
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixtures_checked: int = 0
    adversarial_checked: int = 0

    def fail(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def ok(self) -> bool:
        return not self.errors


def sha256_of(path: Path) -> str:
    """Stream-hash a file; safe for large fixtures."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_schema(report: Report) -> Draft202012Validator | None:
    if not SCHEMA_PATH.is_file():
        report.fail(f"schema.json not found at {SCHEMA_PATH}")
        return None
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.fail(f"schema.json is not valid JSON: {exc}")
        return None
    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        report.fail(f"schema.json is not a valid JSON Schema (draft 2020-12): {exc}")
        return None
    return Draft202012Validator(schema)


def load_manifest(report: Report) -> dict | None:
    if not MANIFEST_PATH.is_file():
        report.fail(f"MANIFEST.yaml not found at {MANIFEST_PATH}")
        return None
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        report.fail(f"MANIFEST.yaml is not valid YAML: {exc}")
        return None
    if not isinstance(data, dict):
        report.fail("MANIFEST.yaml top-level must be a mapping.")
        return None
    for required_key in ("spec_version", "corpus_version", "fixtures", "adversarial"):
        if required_key not in data:
            report.fail(f"MANIFEST.yaml missing required key: {required_key!r}")
    # Empty corpora are allowed in Phase 0; coerce None → {} so downstream is uniform.
    if data.get("fixtures") is None:
        data["fixtures"] = {}
    if data.get("adversarial") is None:
        data["adversarial"] = {}
    return data


def validate_golden_corpus(
    validator: Draft202012Validator, manifest: dict, report: Report
) -> None:
    """Every <name>.<ext> in corpus/<format>/ must have <name>.expected.json + manifest entry."""
    declared = dict(manifest.get("fixtures", {}))  # mutable copy → detect orphans

    if not CORPUS_DIR.is_dir():
        report.fail(f"corpus/ directory not found at {CORPUS_DIR}")
        return

    for format_dir in sorted(CORPUS_DIR.iterdir()):
        if not format_dir.is_dir() or format_dir.name == "adversarial":
            continue
        for fixture_path in sorted(format_dir.iterdir()):
            if not fixture_path.is_file():
                continue
            if fixture_path.suffix == ".json":
                continue  # .expected.json files handled via their pair below
            if fixture_path.name in ("README.md", ".gitkeep"):
                continue

            expected_path = fixture_path.with_suffix(fixture_path.suffix + ".expected.json")
            # Convention: <name>.<ext>.expected.json (NOT <name>.expected.json) so
            # `foo.pdf` and `foo.docx` can coexist without collision.
            if not expected_path.is_file():
                # Try the alternate convention <name>.expected.json
                alt = fixture_path.with_suffix(".expected.json")
                if alt.is_file():
                    expected_path = alt
                else:
                    report.fail(
                        f"fixture {fixture_path.relative_to(SPEC_DIR)} has no "
                        f"sibling .expected.json"
                    )
                    continue

            # Validate the expected.json against schema.json.
            try:
                expected = json.loads(expected_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report.fail(
                    f"{expected_path.relative_to(SPEC_DIR)} is not valid JSON: {exc}"
                )
                continue

            schema_errors = sorted(validator.iter_errors(expected), key=lambda e: e.path)
            for err in schema_errors:
                report.fail(
                    f"{expected_path.relative_to(SPEC_DIR)} schema violation at "
                    f"/{'.'.join(map(str, err.path))}: {err.message}"
                )

            # MANIFEST.yaml hash check.
            rel_key = fixture_path.relative_to(CORPUS_DIR).as_posix()
            manifest_entry = declared.pop(rel_key, None)
            if manifest_entry is None:
                report.fail(
                    f"fixture {fixture_path.relative_to(SPEC_DIR)} missing from "
                    f"MANIFEST.yaml::fixtures. Run `python tooling/hash_fixtures.py`."
                )
            else:
                actual_hash = sha256_of(fixture_path)
                declared_hash = manifest_entry.get("sha256")
                if declared_hash != actual_hash:
                    report.fail(
                        f"fixture {rel_key} hash mismatch: "
                        f"manifest={declared_hash!r} actual={actual_hash!r}. "
                        f"Re-run `python tooling/hash_fixtures.py`."
                    )

            report.fixtures_checked += 1

    # Anything left in `declared` is an orphan manifest entry.
    for orphan in sorted(declared):
        report.fail(
            f"MANIFEST.yaml::fixtures has entry {orphan!r} but no file exists "
            f"at corpus/{orphan}. Remove the entry or restore the file."
        )


def validate_adversarial_corpus(manifest: dict, report: Report) -> None:
    """Adversarial fixtures: hash + `expected` behavior declaration."""
    declared = dict(manifest.get("adversarial", {}))
    adv_root = CORPUS_DIR / "adversarial"
    if not adv_root.is_dir():
        return  # not yet created — fine in Phase 0

    for format_dir in sorted(adv_root.iterdir()):
        if not format_dir.is_dir():
            continue
        for fixture_path in sorted(format_dir.iterdir()):
            if not fixture_path.is_file():
                continue
            if fixture_path.name in ("README.md", ".gitkeep"):
                continue

            rel_key = fixture_path.relative_to(adv_root).as_posix()
            entry = declared.pop(rel_key, None)
            if entry is None:
                report.fail(
                    f"adversarial fixture {fixture_path.relative_to(SPEC_DIR)} "
                    f"missing from MANIFEST.yaml::adversarial."
                )
                continue

            actual_hash = sha256_of(fixture_path)
            if entry.get("sha256") != actual_hash:
                report.fail(
                    f"adversarial fixture {rel_key} hash mismatch."
                )
            expected = entry.get("expected")
            if expected not in ALLOWED_ADVERSARIAL_EXPECTED:
                report.fail(
                    f"adversarial fixture {rel_key} has invalid `expected`: "
                    f"{expected!r}. Must be one of {sorted(ALLOWED_ADVERSARIAL_EXPECTED)}."
                )
            if "provenance" not in entry:
                report.warn(
                    f"adversarial fixture {rel_key} has no `provenance` field "
                    f"(CVE link, original PoC source, or 'synthesized')."
                )

            report.adversarial_checked += 1

    for orphan in sorted(declared):
        report.fail(
            f"MANIFEST.yaml::adversarial has entry {orphan!r} but no file at "
            f"corpus/adversarial/{orphan}."
        )


def main() -> int:
    report = Report()

    validator = load_schema(report)
    manifest = load_manifest(report)

    if validator is None or manifest is None:
        # Bail before downstream checks would spam errors caused by the parent failure.
        print_report(report)
        return 1

    validate_golden_corpus(validator, manifest, report)
    validate_adversarial_corpus(manifest, report)

    print_report(report)
    return 0 if report.ok() else 1


def print_report(report: Report) -> None:
    for w in report.warnings:
        print(f"WARN: {w}", file=sys.stderr)
    for e in report.errors:
        print(f"FAIL: {e}", file=sys.stderr)
    if report.ok():
        print(
            f"OK: {report.fixtures_checked} golden fixture(s), "
            f"{report.adversarial_checked} adversarial fixture(s) validated."
        )
    else:
        print(
            f"FAILED: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s).",
            file=sys.stderr,
        )


if __name__ == "__main__":
    sys.exit(main())
