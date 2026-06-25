# Tolerances — what counts as "equal"

A language implementation passes a golden-corpus test when its `ExtractionResult` differs from the `.expected.json` only within the bounds documented here. Byte-for-byte equality is **not** required; cross-platform/cross-library reality makes that impossible. The tolerances below are the contract.

The canonical values live in [`../MANIFEST.yaml::tolerances`](../MANIFEST.yaml). This document explains them.

## Text equality (`content.text`, `content.pages[*].text`, `content.sections[*].text`)

Comparison is done **after** both sides are normalized via the canonicalizer:

1. NFC-normalize (`unicodedata.normalize('NFC', s)`).
2. Collapse CRLF → LF.
3. Strip trailing whitespace per line.
4. Collapse `\n{3,}` → `\n\n`.
5. Strip leading/trailing whitespace on the whole string.

After canonicalization, the implementation passes iff:

```
levenshtein(actual, expected) / max(1, len(expected)) <= text_levenshtein_pct
```

Default: `text_levenshtein_pct = 0.5%`. This absorbs harmless drift (hyphenation, ligature substitution, soft-hyphen handling) without masking genuine extraction bugs.

If a fixture needs a tighter or looser bound (e.g. a `txt` fixture should be byte-equal), pin it per-fixture in `MANIFEST.yaml::fixtures[<path>].tolerance_override`.

## Timestamps (`metadata.created`, `metadata.modified`)

Parse both sides as `datetime`. Pass iff `abs(actual - expected) <= metadata_date_seconds` (default 1 s). Absorbs timezone-parsing drift across languages.

## Metadata strings (`metadata.title`, `metadata.author`, …)

After whitespace-trimming both sides:

- `null` and `null` → equal.
- `null` and string → **not equal** (silent metadata loss is a bug).
- string and string → exact equality after NFC normalization.

## `metadata.extra`

- Actual `extra` may **omit** keys present in expected (the impl does not extract that namespace yet). This is recorded as a `WARN` in the golden test, not a failure.
- Actual `extra` **must not contain** keys absent from `docs/schema-fields.md::Currently allocated extra keys`. Unknown keys are a contract violation.
- Where both sides have a key, values must match exactly.

## `warnings`

Order-independent set equality. The implementation passes iff:
- Every warning in `expected.warnings` is present in `actual.warnings` (or matches by stable prefix — see `schema-fields.md::warnings`).
- Extra warnings in `actual` are permitted (impls may surface more detail).

## `source`

- `mime_type`: exact match. A MIME-detection bug is a real bug.
- `sha256`: exact match (it's a hash of the input — must agree).
- `size_bytes`: exact match.
- `filename`: not compared (informational).

## `extractor`

Not compared. Each impl writes its own name/version.

## Adversarial corpus (different contract)

Fixtures under `corpus/adversarial/` are compared **behaviorally**, not by output:

- Some assert a specific `ExtractError` subclass is raised (typed in `expected.json::expected_error`).
- Some assert specific `warnings` appear and no execution side-effect happens (no network call, no disk write outside the configured tmpdir).
- See [`adding-a-format.md`](adding-a-format.md) for the adversarial fixture template.

## Why these specific numbers?

| Tolerance | Empirical basis |
|---|---|
| `text_levenshtein_pct: 0.5%` | PyMuPDF vs pdfplumber differ ~0.1–0.3% on real-world PDFs; 0.5% has headroom without masking the "lost a paragraph" class of bug. |
| `metadata_date_seconds: 1` | Python `datetime`, JS `Date`, Go `time.Time` all round-trip ISO 8601 with sub-second precision but with different epoch handling; ±1s avoids spurious failures. |

Tightening any value is a major spec bump (existing impls may regress). Loosening is a minor bump.
