# Golden corpus — MSG (Outlook)

**Target coverage**:
- `plain-text.msg` — plain body, no attachments.
- `html-body.msg` — HTML body; extractor converts to text per HTML rules.
- `with-attachments.msg` — body text only; attachment metadata in `metadata.extra.msg:attachments`.
- `non-utf8.msg` — exercise charset detection.
