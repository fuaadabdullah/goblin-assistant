# PDF Attachment Extraction

This service extracts text from uploaded PDF attachments at upload time and
injects relevant chunks into chat context when those attachments are referenced.

## Runtime Flags

- `GOBLIN_PDF_OCR_ENABLED` (default: `false`)
  - `false`: only text-based extraction via `pypdf`.
  - `true`: if no extractable text is found, attempts OCR as a fallback.
- `GOBLIN_ATTACHMENT_CONTEXT_MAX_CHUNKS` (default: `5`)
  - Maximum selected PDF chunks injected per message.
- `GOBLIN_ATTACHMENT_CONTEXT_MAX_CHARS` (default: `5000`)
  - Character budget for all injected PDF context in one message.

## OCR Dependencies (Optional)

OCR is optional and only used when `GOBLIN_PDF_OCR_ENABLED=true`.

Python packages:
- `pytesseract`
- `pdf2image`

System packages:
- `tesseract-ocr`
- Poppler utilities (used by `pdf2image`)

If OCR dependencies are missing, upload still succeeds and extraction metadata
returns a non-fatal warning/status (`ocr_missing_deps`).
