# knovas-extract-spec

[![CI](https://github.com/Seifeddini/knovas-extract-spec/actions/workflows/ci.yml/badge.svg)](https://github.com/Seifeddini/knovas-extract-spec/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Cross-language contract + golden corpus + adversarial corpus for the `knovas-extract-<lang>` family of client libraries. **This repo is the source of truth.** Every language implementation must produce output matching this corpus at a pinned `spec_version`.

## Why spec-first?

Clients wanted extraction libraries in many languages (Python, then Node, Go, Rust, Java, …). Two architectures could deliver that:

| Architecture | Cost |
|---|---|
| Single core (Rust/Tika) + thin wrappers | Single implementation, but FFI overhead / JVM dependency / weak Rust parser ecosystem |
| **Per-language native, governed by a shared spec** ← we chose this | Each language uses its best native libs; cross-language consistency enforced by this corpus |

A `knovas-extract-node` PR is "correct" iff it passes the golden corpus at the pinned `spec_version`. No language can drift silently.

## Layout

```
.
├── schema.json          # JSON Schema 2020-12 — the contract
├── MANIFEST.yaml        # spec_version, corpus_version, fixture hashes, tolerances
├── CHANGELOG.md
├── docs/
│   ├── schema-fields.md   # field-by-field semantics + examples
│   ├── tolerances.md      # what "equal" means across languages
│   ├── adding-a-format.md
│   └── adding-a-language.md
├── tooling/
│   ├── validate_corpus.py            # CI gate
│   ├── hash_fixtures.py              # maintainer: refresh MANIFEST.yaml
│   ├── diff_extraction.py            # contributor: tolerance-aware diff
│   └── generate_synthetic_fixtures.py # regenerate deterministic fixtures
└── corpus/
    ├── pdf/  docx/  msg/  eml/  html/  rtf/  txt/  md/   # golden
    ├── torture/                                          # malformed/edge
    └── adversarial/                                      # known-bad inputs
```

## Language implementations

| Language | Repo | Pinned spec | Status |
|---|---|---|---|
| Python | [knovas-extract-python](https://github.com/Seifeddini/knovas-extract-python) | 1.0.0 | shipped (0.1.0) |
| Node | _TBD_ | — | planned |
| Go | _TBD_ | — | planned |
| Rust | _TBD_ | — | planned |

## Quickstart (maintainer)

```bash
git clone https://github.com/Seifeddini/knovas-extract-spec.git
cd knovas-extract-spec
pip install jsonschema PyYAML pymupdf python-docx
python tooling/validate_corpus.py
```

## Adding a fixture

1. Drop the input file in `corpus/<format>/<name>.<ext>` (or use `tooling/generate_synthetic_fixtures.py` for deterministic synthetic ones).
2. Run your language implementation against it and hand-curate the `<name>.expected.json` (golden ≠ "whatever the parser produced today"; golden is **the truth**).
3. `python tooling/hash_fixtures.py` to refresh `MANIFEST.yaml`.
4. `python tooling/validate_corpus.py` must report OK.
5. Open a PR.

Detailed contributor docs in [`docs/adding-a-format.md`](docs/adding-a-format.md) and [`docs/adding-a-language.md`](docs/adding-a-language.md).

## Versioning

- **`spec_version`** — `major.minor.patch`. Bumps when `schema.json` changes. Major bumps are breaking; every language implementation must be updated before it can claim conformance to the new major.
- **`corpus_version`** — calver `YYYY.MM.DD`. Bumps whenever fixtures change. Non-breaking by definition (a new fixture only adds a new gate).

Language implementations pin both versions in their build config and refuse to publish a release if validation fails.

## Security note

The `corpus/adversarial/` directory contains **deliberately malicious inputs** — decompression bombs, XXE payloads, encrypted documents, RTF object-linking PoCs. Treat the directory as untrusted; do not open fixtures in a viewer outside a sandbox. Provenance for every PoC is recorded in `corpus/adversarial/README.md` and `MANIFEST.yaml::adversarial[*].provenance`.

To report a parser exploit not covered here, **do not** open a public PR. Email `security@knovas.ch` per the policy in each language repo's `SECURITY.md`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
