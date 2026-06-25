# Adversarial corpus — KNOWN-BAD inputs

**WARNING: this directory contains deliberately malicious files.** Do not open fixtures with viewers/editors outside a sandbox. Files are tracked in Git LFS and shipped to CI; treat the entire subtree as untrusted.

## Purpose

Regression tests for the security posture in [`/plans/our-client-asked-if-bright-pony.md::Part 3`](../../../../../C:/Users/siran/.claude/plans/our-client-asked-if-bright-pony.md). Every extractor must degrade gracefully on these inputs — typed error, or sanitized output with a specific warning — without RCE, network egress, disk write, or process death.

## Provenance template

Every fixture must have an entry below recording where it came from, when it was added, and why it can be safely redistributed (synthesized, derived from a public CVE PoC, or contributed by a researcher who waived rights). Without provenance, the fixture is rejected by `validate_corpus.py`.

```yaml
# Template — copy + fill in when adding a fixture.
- path: pdf/encrypted.pdf
  added: 2026-06-25
  added_by: <maintainer handle>
  cve: null                  # or "CVE-2019-XXXXX"
  source: synthesized        # or "public PoC at <url>", "private report"
  redaction: none            # or "real PoC redacted; behavioral pattern preserved"
  expected_behavior: EncryptedDocumentError
```

## Fixture list

_(Phase 0: empty. Adversarial fixtures land in Phase 3+ alongside their format implementations.)_

## What goes here vs `../torture/`

| Question | Adversarial | Torture |
|---|---|---|
| Was this constructed to exploit a parser? | yes | no |
| Could it crash, RCE, or exfiltrate? | designed to | unintentional bug |
| Provenance record required? | yes (this README + MANIFEST.yaml) | no |
| Git LFS required? | always | only if > 1 MB |

## Reporting a new attack vector

If you discover a parser exploit not covered here, **do not** open a public PR with the PoC. Email `security@knovas.ch` (GPG key in `SECURITY.md`). After triage and patch, we add a redacted regression fixture here.
