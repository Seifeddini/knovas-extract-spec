# Golden corpus — PDF

Each PDF fixture must have a sibling `<name>.pdf.expected.json` (or `<name>.expected.json`) and an entry in [`../../MANIFEST.yaml::fixtures`](../../MANIFEST.yaml).

**Target coverage**:
- `text-only.pdf` — single column, no images.
- `multi-column.pdf` — two- or three-column layout (e.g. academic paper).
- `tabular.pdf` — pages with tables (verify the parser doesn't mangle row order).
- `multilingual-de-fr.pdf` — mixed German/French; verifies language detection.
- `scanned-no-ocr.pdf` — image-only PDF; expected `content.text == ""` + warning `"no extractable text (consider OCR)"`.

See [`../../docs/adding-a-format.md`](../../docs/adding-a-format.md).
