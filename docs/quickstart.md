# Quickstart — using a knovas-extract library

The friendly version. If you're contributing or building a new language
implementation, see [`architecture.md`](architecture.md).

## Python (`knovas-extract`)

### Install

```bash
pip install knovas-extract                       # core (TXT/MD/HTML/EML)
pip install 'knovas-extract[pdf]'                # + PyMuPDF (AGPL — read NOTICE)
pip install 'knovas-extract[docx,msg,rtf]'       # + DOCX/MSG/RTF
pip install 'knovas-extract[all]'                # everything
```

License-sensitive embedders: install `knovas-extract[minimal]` for the
permissive-only subset (no AGPL / no GPL deps). Calling `extract()` on a
format that needs an unavailable backend raises `DependencyMissingError`
with the exact `pip install` command to fix it.

### Extract a file

```python
from knovas_extract import extract

r = extract("report.pdf")

print(r.content.text)            # canonicalized text
print(r.metadata.title)          # "Q4 Earnings" (or None)
print(r.metadata.page_count)     # 12
for page in r.content.pages:     # per-page text (when paginated)
    print(page.index, page.text[:80])
print(r.warnings)                # ["page 7: unrecognized font", ...]
```

Bytes work too:

```python
data = open("report.pdf", "rb").read()
r = extract(data, mime="application/pdf")
```

Pass `mime=` explicitly when you have ambiguous content (e.g. a `.docx` that
might be detected as `application/zip`). The library otherwise sniffs by file
header (libmagic) with filename-extension fallback.

### Resource limits

Every extraction is bounded. Override per call:

```python
from knovas_extract import extract, Limits

r = extract(
    "huge.docx",
    limits=Limits(
        max_input_bytes=50 * 1024 * 1024,    # 50 MiB cap
        max_pages=1_000,
        max_decompression_ratio=50,          # ZIP-bomb guard
        max_text_bytes=10 * 1024 * 1024,
    ),
)
```

When a limit is crossed you get a `ResourceExhaustedError` with `.what`,
`.limit`, `.observed` attributes.

### Typed errors

Every call either returns an `ExtractionResult` or raises a subclass of
`ExtractError`:

| Exception | When |
|---|---|
| `UnsupportedFormatError` | MIME not registered |
| `CorruptDocumentError` | Bytes couldn't be parsed as the claimed format |
| `EncryptedDocumentError` | Password-protected document, no password supplied |
| `ResourceExhaustedError` | A `Limits` threshold was crossed |
| `DependencyMissingError` | An optional `[extra]` isn't installed — message tells you the exact `pip install` command |

No bare exceptions, no `None`, no `Optional[ExtractionResult]`.

### Run inside a sandbox (recommended for untrusted input)

```bash
# Linux + bubblewrap
bwrap --unshare-all --share-net no --die-with-parent \
      --tmpfs /tmp --ro-bind / / \
      --bind /path/to/document.pdf /tmp/in.pdf \
      python -m knovas_extract /tmp/in.pdf > /tmp/out.json
```

Recipes for `bubblewrap`, `nsjail`, and rootless containers (with seccomp
profile) in the Python repo's
[`docs/sandboxing.md`](https://github.com/Seifeddini/knovas-extract-python/blob/main/docs/sandboxing.md).

### CLI

```bash
knovas-extract /path/to/document.pdf            # JSON to stdout
knovas-extract --pretty /path/to/document.pdf   # indented
knovas-extract --mime application/pdf bytes.bin # override MIME detection
```

### Verify a release before installing in production

```bash
python -m sigstore verify identity \
  --cert-identity 'https://github.com/Seifeddini/knovas-extract-python/.github/workflows/release.yml@refs/tags/v0.1.0' \
  --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
  knovas_extract-0.1.0-py3-none-any.whl

slsa-verifier verify-artifact knovas_extract-0.1.0-py3-none-any.whl \
  --provenance-path knovas_extract-0.1.0.intoto.jsonl \
  --source-uri github.com/Seifeddini/knovas-extract-python \
  --source-tag v0.1.0
```

Full recipe in the Python repo's `RELEASING.md`.

## Other languages

The other implementations don't exist yet. To stand one up, see
[`adding-a-language.md`](adding-a-language.md) — the recipe is structurally
identical (pin the spec, implement the public API, pass the golden + adversarial
corpora, ship Sigstore-signed releases) but the implementation is real
engineering per language.

## "How do I…?" recipes

### Extract a Semantix-ingest-ready stream

```python
from knovas_extract import extract

r = extract("contract.docx")

# Push to /secured/init_document_transmission, then each page as a part:
init_payload = {
    "part_count": len(r.content.pages or [r.content]),
    "identifier": r.source.filename or r.source.sha256[:16],
    "title": r.metadata.title,
    "path": "/uploads/contract.docx",
}

for i, page in enumerate(r.content.pages or [type("P", (), {"text": r.content.text})()]):
    yield {"part_number": i, "snippet": page.text, "page_number": i}
```

### Detect (but not extract) the MIME type only

```python
from knovas_extract.dispatch import _detect_mime
mime = _detect_mime(data, filename="x.pdf")
```

### Filter for documents that contain a specific term

```python
from knovas_extract import extract

docs = []
for path in Path("incoming/").iterdir():
    try:
        r = extract(path)
    except ExtractError:
        continue
    if "deadline" in r.content.text.lower():
        docs.append((path, r.metadata.title))
```

### Cross-language conformance check

If you're building a new language implementation, the smallest unit of
correctness is:

```bash
# In your language repo
git clone https://github.com/Seifeddini/knovas-extract-spec.git tests/spec
your-language-test-runner tests/golden -- against tests/spec/corpus/
your-language-test-runner tests/adversarial -- against tests/spec/corpus/adversarial/ \
    --behavior-from tests/spec/MANIFEST.yaml
```

When both pass at a pinned `spec_version`, you can ship.
