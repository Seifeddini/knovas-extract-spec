# Golden corpus — RTF

**Target coverage**:
- `simple.rtf` — plain text in RTF wrapping.
- `formatted.rtf` — bold/italic/lists; formatting stripped, structure preserved.
- `with-image.rtf` — image bytes ignored.

> **Security note**: never add an RTF fixture with object-linking (`\object`) here; those belong in `corpus/adversarial/rtf/` with `expected: sanitized` and a provenance record (CVE-2017-0199 and friends).
