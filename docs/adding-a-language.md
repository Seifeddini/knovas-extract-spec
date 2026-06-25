# Adding a new language implementation

A new `knovas-extract-<lang>` repo is a real engineering project: pick the best native libraries for that language, satisfy the security posture in `/plans/our-client-asked-if-bright-pony.md::Part 3`, and pass the golden + adversarial corpora. This doc is the recipe.

## Prerequisites

- The language has mature, maintained libraries for ≥80% of the v1 formats (PDF, DOCX, TXT, MD, MSG, EML, HTML, RTF). For gaps, document a fallback (often: shell out to a Tika sidecar for that one format).
- A maintainer with ownership commitment ≥12 months. Languages without an owner do not get added.
- Demand: at least one paying client has asked for this language, or it's part of a published roadmap.

## Steps

### 1. New repo

`github.com/knovas/knovas-extract-<lang>`. Apache-2.0. Branch protection on `main` (signed commits, required reviews, required status checks, no admin bypass). CODEOWNERS file gating all PRs.

### 2. Pin the spec

In your build config (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, …), pin both `spec_version` and `corpus_version`. The spec/corpus are consumed via:

- **Git submodule** at `tests/spec/` pointing at this monorepo (simplest), OR
- **Tarball** downloaded from a GitHub Release of the monorepo (more CI-friendly).

Pick one and document it in your repo's `RELEASING.md`.

### 3. Implement the public API

Every language implementation must expose, idiomatically:

- A single `extract(input, *, mime?, limits?) → ExtractionResult` entry point.
- An `ExtractionResult` type that round-trips through `schema.json` JSON.
- A typed error hierarchy rooted at `ExtractError`, with at minimum: `UnsupportedFormatError`, `CorruptDocumentError`, `EncryptedDocumentError`, `ResourceExhaustedError`, `DependencyMissingError`.
- An `IExtractor` protocol/interface with `supported_mimes` and `extract(bytes) → ExtractionResult`. Each format extractor implements this.

Naming follows language convention (`snake_case` in Python, `camelCase` in JS, etc.), but the JSON output is identical.

### 4. Wire the full quality-gate suite

Required gates (mirror what the Python repo ships; see plan Part 3):

- Lint + type-check (language-native).
- **Security lint** (language-native; `bandit`+`semgrep` for Python, `gosec` for Go, `cargo-audit` for Rust, …).
- **Dependency CVE scan** (`osv-scanner` works for every ecosystem).
- **CodeQL** (supports Go, Java, JS/TS, Python, Ruby, C/C++, Swift, Kotlin).
- **Coverage-guided fuzzing** (atheris for Python, go-fuzz for Go, cargo-fuzz for Rust, jazzer for Java, jsfuzz for JS).
- **OSS-Fuzz integration** once the project is stable.
- **Memory-safety** if the impl wraps C/C++ libraries (ASan/UBSan job nightly).
- **Network-isolation** assertion in test suite (no socket calls).
- **Resource-limit** tests inside a cgroup.
- **SLSA L3 build provenance + Sigstore signing + SBOM** at release time.
- **OIDC trusted publisher** to the language's package registry (PyPI / npm / crates.io / Maven Central / …).

The acceptance gate is: every gate green AND golden corpus passes AND adversarial corpus passes. No exceptions.

### 5. Implement the formats in order

Phased delivery, mirroring the Python repo:

1. TXT + MD (proves the pipeline).
2. PDF + DOCX (the high-volume formats, requires differential testing).
3. MSG + EML + HTML + RTF (round out v1).

Each format ships behind a CI gate that runs the corresponding `corpus/<format>/` and `corpus/adversarial/<format>/` slices.

### 6. External security audit

Before `0.1.0`, commission a third-party audit (Trail of Bits / NCC / Cure53 / equivalent) scoped to dispatch + every extractor + supply-chain configuration. Publish the report. Address all findings rated medium+ before publishing.

### 7. Register the impl

Once you ship `0.1.0`:

- Add a row to [`../../../docs/Docs/04_COMPONENTS/client_extraction_libraries.md`](../../../docs/Docs/04_COMPONENTS/client_extraction_libraries.md)::Language matrix with repo URL, package registry, current pinned `spec_version`, audit date.
- Open a PR against this monorepo's `clients/extraction/spec/MANIFEST.yaml::implementations` adding `{ name, version, spec_version, repo_url }`. The monorepo's nightly `spec-conformance` job will start tracking your repo.

## Notes for specific languages

| Language | Recommended libraries | Watchouts |
|---|---|---|
| Python | PyMuPDF (AGPL), python-docx, extract-msg, selectolax, striprtf | PyMuPDF licensing review per client |
| Node/TS | pdfjs-dist (Mozilla), mammoth, msgreader, parse5 | pdfjs is slow at scale — consider mupdf-via-WASM for hot path |
| Go | unidoc (commercial) OR ledongthuc/pdf, mail-parser via cgo | Pure-Go DOCX is weak; consider Tika sidecar fallback |
| Rust | lopdf, docx-rs, mail-parser | Rust DOCX/MSG ecosystem is thin; expect to wrap C libs |
| Java | Apache Tika, PDFBox, POI | Easiest format coverage; heavyweight JAR is the price |

## Anti-patterns

- **Don't ship without the adversarial corpus passing.** A "fast" parser that crashes on a decompression bomb is worse than no parser.
- **Don't reimplement the spec docs in your repo's README.** Link here; keep one source of truth.
- **Don't add language-specific `metadata.extra` keys without a spec PR.** Drift defeats the entire point of the shared spec.
