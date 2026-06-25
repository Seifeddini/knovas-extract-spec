# `ExtractionResult` — field semantics

Field-by-field reference for [`schema.json`](../schema.json). When the contract and the prose disagree, the JSON Schema wins; file a PR.

## Top-level

| Field | Type | Required | Notes |
|---|---|---|---|
| `spec_version` | `"X.Y.Z"` | yes | Must match the `spec_version` in the runtime spec the implementation pins. Mismatch → implementation must refuse to publish output. |
| `source` | object | yes | Provenance of the input bytes. **Computed by the extractor**, not parsed from the file. |
| `metadata` | object | yes | Document-level metadata; every field nullable. |
| `content` | object | yes | Extracted text. `text` always present; `pages` / `sections` only when meaningful for the format. |
| `warnings` | string[] | yes | Empty array if none. Used for "macros stripped", "page 7 had unrecognized font", etc. |
| `extractor` | object | yes | Identifies the implementation that produced this result. |

## `source`

| Field | Notes |
|---|---|
| `mime_type` | IANA media type. Detected via header/magic-bytes (libmagic / equivalent). **Never** trust the file extension — polyglot files are real. |
| `sha256` | Hash of the raw input bytes, lowercase hex. Stable identity across implementations. |
| `size_bytes` | Raw input size. Implementations should refuse files exceeding their configured `Limits.max_input_bytes`. |
| `filename` | Original filename if known. Informational only; never used to dispatch. |

## `metadata`

All fields **nullable**. `null` means "the extractor did not find this", not "the document had an empty value". Implementations must not invent values.

| Field | Notes |
|---|---|
| `title`, `author` | Verbatim from document metadata; whitespace-trimmed. |
| `language` | BCP-47 tag if reliably detected (`'de'`, `'en-US'`); otherwise `null`. Implementations may use heuristic language detection. |
| `created`, `modified` | ISO 8601 timestamps. Tolerance ±1 s when comparing across implementations (timezone parsing varies). |
| `page_count` | Pages in the source (NOT in `content.pages` — those may be capped by `Limits`). |
| `word_count` | Whitespace-separated token count of `content.text`. Implementations should compute this themselves rather than trusting source metadata. |
| `extra` | Format-specific keys, namespaced (`pdf:producer`, `docx:revision`, `eml:message_id`). A language implementation **may omit** keys it does not extract; it **must not invent** keys not documented here. |

### Currently allocated `extra` keys

| Namespace | Key | Format |
|---|---|---|
| `pdf:` | `producer`, `creator`, `pdf_version` | PDF |
| `docx:` | `revision`, `template`, `last_printed` | DOCX |
| `eml:` / `msg:` | `message_id`, `from`, `to`, `cc`, `subject_prefix`, `has_attachments` | EML / MSG |
| `html:` | `charset_declared`, `description`, `keywords` | HTML |

Adding a key requires a spec PR.

## `content`

### `text`

- **Always present**, even if empty (e.g. scanned-image PDF with no OCR → empty string + warning).
- **NFC-normalized** (`unicodedata.normalize('NFC', s)`).
- **LF newlines** (`'\n'`), never CRLF, regardless of source.
- **Trailing whitespace stripped** per line.
- **Max one blank line** between paragraphs (`\n{3,}` → `\n\n`).
- No leading/trailing whitespace on the document as a whole.

These rules let `text` compare across languages without per-platform noise.

### `pages` (nullable)

Present only when the format is naturally paginated (PDF, paginated DOCX export). Each entry: `{ "index": 0-based, "text": <same rules as content.text> }`. Sum of `pages[*].text` is **not** required to equal `content.text` (extractors may apply different join logic between pages, e.g. footnote merging).

### `sections` (nullable)

Present only when the document carries heading structure (DOCX `Heading 1..6`, HTML `<h1>..<h6>`, MD `#..######`). Flat list (not nested), in document order. `level` ∈ [1, 6]. Implementations may merge consecutive same-level sections.

## `warnings`

Free-form, human-readable strings. Stable prefixes are encouraged for diffability:

- `"macros stripped"` — DOCX/PPTX macros encountered and ignored.
- `"javascript dropped"` — PDF embedded JS encountered and ignored.
- `"page N: unreadable font"` — partial extraction failure.
- `"truncated at <limit>"` — output was capped by `Limits`.

Warnings are part of the contract; adversarial-corpus tests assert specific warnings appear.

## `extractor`

Used by `tooling/diff_extraction.py` to attribute regressions across implementations. Both fields are recorded in nightly soak reports.

| Field | Example |
|---|---|
| `name` | `"knovas-extract-python"` |
| `version` | `"0.1.0"` |
