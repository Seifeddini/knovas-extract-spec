# Torture corpus — malformed / pathological inputs

Distinct from [`../adversarial/`](../adversarial/). Torture fixtures are **non-malicious** edge cases that historically caused parser bugs:

- Truncated files (last 1–100 bytes chopped off).
- Files with claimed MIME mismatching content.
- Zero-byte files.
- One-byte files.
- Files at exactly the configured size limit.

Each fixture's expected behavior is recorded in its `.expected.json` (typed error class or graceful empty result).

Genuinely malicious inputs (decompression bombs, XXE, RTF object-linking, …) go in `../adversarial/`.
