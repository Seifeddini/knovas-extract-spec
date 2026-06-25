# Adding a new format to the spec

A "format" is a new MIME type the extraction libraries claim to support (e.g. adding `.xlsx`, `.epub`, `.pages`). Adding one is a deliberate, multi-step spec change.

## Decision gate

Before opening a PR, confirm:

- [ ] At least two language implementations have a mature library for the format (otherwise we're locking in a Python-only feature behind a "cross-language" facade).
- [ ] The format has documented, stable extraction semantics (cells in XLSX, slides in PPTX, …). If it doesn't, write them down first as a separate doc.
- [ ] Adversarial corpus is feasible (we can construct decompression-bomb / zip-slip / XXE variants).
- [ ] An extractor maintainer is willing to own the format long-term.

If any check fails, the format goes on the backlog instead.

## Steps

### 1. Update `schema.json` if needed

Most formats fit the existing schema. If the format needs new `metadata.extra.*` namespaces, allocate them in `docs/schema-fields.md::Currently allocated extra keys` **first**. Bumping `spec_version.minor` is enough; new optional `extra` keys are non-breaking.

### 2. Create the corpus directory

```
clients/extraction/spec/corpus/<format>/
├── simple.<ext>
├── simple.expected.json
├── <three more representative variants>.<ext>
└── <their .expected.json>
```

Minimum: **3 golden fixtures** spanning the realistic shape of the format (e.g. for `xlsx`: one sheet, multi-sheet, formulas-with-cached-values).

### 3. Create adversarial fixtures

In `corpus/adversarial/<format>/`, add at minimum:

- **Decompression bomb** (if the format is ZIP-based): expected `ResourceExhaustedError`.
- **Path-traversal** (zip-slip, if ZIP-based): expected `CorruptDocumentError`; never writes outside the configured tmpdir.
- **Truncated** (chop the last 100 bytes off a valid file): expected `CorruptDocumentError`.
- **Polyglot** (a valid file that is also a valid file of another format): dispatch picks based on header bytes, not extension.

Each adversarial fixture **must** include a provenance note in `corpus/adversarial/README.md` (CVE link if applicable, original PoC source, redaction notes).

### 4. Register in `MANIFEST.yaml`

Run:

```bash
python clients/extraction/spec/tooling/hash_fixtures.py
```

This refreshes the `fixtures` and `adversarial` maps with SHA-256 hashes and sizes. Hand-edit the resulting entries to add `tags` (helps test filtering).

### 5. Bump `corpus_version`

`MANIFEST.yaml::corpus_version` → today's date (`YYYY.MM.DD`).

### 6. Validate

```bash
python clients/extraction/spec/tooling/validate_corpus.py
```

Must report `OK`.

### 7. Land the spec PR

Once merged, every `knovas-extract-<lang>` repo's `spec-sync` nightly job will detect the new fixtures and open a PR against itself adding the new extractor. Language maintainers then implement the format and merge when their CI is green.

## Anti-patterns

- **Don't add a format just because one client asked.** The 5-language matrix means each format is ≥5× the work it appears to be.
- **Don't ship a format without adversarial fixtures.** Parser code on untrusted input is an attack surface; "we'll add the security tests later" is how CVEs ship.
- **Don't put fixtures larger than 5 MB without LFS.** `.gitattributes` enforces this; if you have a giant fixture, justify it in the PR.
