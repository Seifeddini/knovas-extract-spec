# Golden corpus — HTML

**Target coverage**:
- `simple.html` — standard document with `<title>`, headings, paragraphs.
- `js-heavy.html` — extractor must NOT execute scripts; script content not in output.
- `malformed.html` — broken nesting; extractor recovers gracefully.
- `with-meta.html` — exercises `metadata.extra.html:*` extraction (description, keywords, charset_declared).
