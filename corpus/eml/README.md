# Golden corpus — EML (RFC 822 email)

**Target coverage**:
- `plain.eml` — text/plain only.
- `multipart-html.eml` — multipart/alternative with text + HTML; extractor prefers text/plain when present.
- `with-attachment.eml` — body text only; attachment metadata in extra.
- `non-ascii-headers.eml` — RFC 2047 encoded-word headers.
