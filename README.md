# Knovas Extraction Spec

Cross-language contract + golden corpus for the `knovas-extract-<lang>` family of client libraries. **This directory is the source of truth.** Every language implementation must produce output that matches the corpus at a pinned spec version.

## Why spec-first?

Clients asked for extraction libraries in many languages (Python first, then Node, Go, Rust, Java, …). Two architectures could deliver that:

| Architecture | What it costs |
|---|---|
| Single core (Rust/Tika) + thin wrappers | Single implementation, but FFI overhead / JVM dependency / weak Rust parser ecosystem |
| **Per-language native, governed by a shared spec** ← we chose this | Each language uses its best native libs; cross-language consistency enforced by this corpus |

The shared spec means: a `knovas-extract-node` PR is "correct" iff it passes the golden corpus at the pinned `spec_version`. No language can drift silently.

## Layout

```
spec/
├── schema.json          # JSON Schema for ExtractionResult (the contract)
├── MANIFEST.yaml        # spec_version, corpus_version, fixture hashes, tolerances
├── CHANGELOG.md
├── docs/
│   ├── schema-fields.md   # field-by-field semantics + examples
│   ├── tolerances.md      # what "equal" means across languages
│   ├── adding-a-format.md
│   └── adding-a-language.md
├── tooling/
│   ├── validate_corpus.py   # CI: every .expected.json valid + hashed
│   ├── hash_fixtures.py     # maintainer: regenerate MANIFEST.yaml hashes
│   └── diff_extraction.py   # contributor: human-readable diff vs golden
└── corpus/
    ├── pdf/                 # input + .expected.json per fixture
    ├── docx/  msg/  eml/  html/  rtf/  txt/  md/
    ├── torture/             # malformed / pathological inputs (typed-error contract)
    └── adversarial/         # known-bad inputs (security regression tests)
```

## Quickstart

**Validate the corpus** (every PR runs this in CI):

```bash
python clients/extraction/spec/tooling/validate_corpus.py
```

**Add a new fixture**:

1. Drop the input file in `corpus/<format>/<name>.<ext>`.
2. Generate the golden output by running your language implementation against it (e.g. `python -m knovas_extract dump my.pdf > corpus/pdf/my.expected.json`).
3. Hand-edit the `expected.json` to reflect what the contract *should* return (golden ≠ "whatever the parser produced today" — golden is the truth).
4. Run `python clients/extraction/spec/tooling/hash_fixtures.py` to refresh `MANIFEST.yaml`.
5. Run `validate_corpus.py` and open a PR.

**Add a new format**: see [`docs/adding-a-format.md`](docs/adding-a-format.md).

**Add a new language implementation**: see [`docs/adding-a-language.md`](docs/adding-a-language.md).

## Versioning

- **`spec_version`** (major.minor.patch) — bumps when `schema.json` changes. Major bumps are breaking; all language implementations must be updated before they can claim conformance.
- **`corpus_version`** (calver `YYYY.MM.DD`) — bumps when fixtures change. Non-breaking by definition (a new fixture only adds a new gate).

Language implementations pin both versions in their build config and refuse to publish a release if validation fails.

## Security note

The `adversarial/` directory contains **deliberately malicious inputs** (decompression bombs, XXE payloads, RTF object-linking PoCs, etc.) used to verify our extractors degrade gracefully. Treat the directory as untrusted; do not open fixtures in a viewer outside a sandbox. Provenance for every PoC is recorded in `adversarial/README.md`.

## Plan reference

This scaffold implements **Phase 0** of [`/plans/our-client-asked-if-bright-pony.md`](../../../C:/Users/siran/.claude/plans/our-client-asked-if-bright-pony.md). Phase 1 adds fixtures; Phase 2+ stand up the language implementations in separate repos (`knovas/knovas-extract-python` first).
