# Changelog — Knovas extraction spec

All notable changes to `schema.json`, `MANIFEST.yaml`, the corpus, and the tooling are recorded here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/) and is tracked independently in `MANIFEST.yaml::spec_version` (schema) and `MANIFEST.yaml::corpus_version` (fixtures).

A **major** spec bump is a breaking change to the JSON contract; every language implementation must be updated before they can claim conformance to the new version.

## [Unreleased]

### Added
- Initial scaffold: `schema.json` v1.0.0, `MANIFEST.yaml`, validation tooling, contributor docs.
- Empty corpus directories for: pdf, docx, msg, eml, html, rtf, txt, md, torture, adversarial.

[Unreleased]: https://github.com/knovas/KnowledgeBase/compare/develop...HEAD
