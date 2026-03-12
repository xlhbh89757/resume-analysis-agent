# OCR and Legacy DOC Parsing Design

**Goal:** Improve resume parsing for scanned/image PDFs and legacy `.doc` files without changing the existing LLM structuring flow.

**Problem Statement**
- Some PDFs are visually readable but contain no text layer. Current extractors (`pypdf2`, `pymupdf`, `pdfplumber`) return zero text and the task dies with `Failed to extract readable text from PDF`.
- Some `.doc` and pseudo-`.docx` files are routed to `python-docx`. Real legacy `.doc` files are OLE binaries and fail with `Package not found`.
- The current pipeline is missing two capabilities: OCR fallback and file content based routing.

**Recommended Approach**
1. Keep the current text-first path for normal text PDFs and valid DOCX files.
2. Add file signature detection before parsing. Route by actual content, not only file suffix.
3. Add OCR fallback for:
   - scanned/image PDFs
   - image files (`jpg`, `jpeg`, `png`)
   - converted `.doc -> pdf` files when the converted PDF still has no text layer
4. Add LibreOffice based conversion for real legacy `.doc` files.
5. Keep the current LLM extraction stage unchanged. OCR/conversion only feeds better text into it.

**Architecture**
- `URLStructuringService` continues to download files and provide a local temp path.
- `DocumentParser` becomes responsible for:
  - content signature detection
  - text extraction path selection
  - OCR fallback when text extraction fails or is too weak
  - `.doc` conversion through LibreOffice
- OCR is a fallback, not the default path. This keeps cost and latency bounded.

**Detection Rules**
- PDF: starts with `%PDF`
- DOCX: ZIP signature `PK...` and parseable as OOXML package
- DOC: OLE signature `D0 CF 11 E0 A1 B1 1A E1`
- Image: common image suffixes or image mime/file signature
- Unknown: explicit parse error with a clear unsupported-file error code

**OCR Strategy**
- Use `RapidOCR` locally.
- Trigger OCR only when:
  - PDF extractors all return empty text, or
  - extracted text is low quality, or
  - file is an image.
- Prefer preserving information over aggressive cleanup. Clean only obvious OCR noise.

**DOC Strategy**
- Use local `soffice --headless` conversion for real `.doc` files.
- Convert `.doc -> pdf`.
- Re-enter the PDF flow after conversion.
- If LibreOffice is unavailable or conversion fails, raise a dedicated conversion error.

**Error Handling**
- Add more explicit parse error categories for later task/deadletter reporting:
  - `E_CONVERT_DOC`
  - `E_OCR`
  - `E_UNSUPPORTED_FILE`
- Keep existing deadletter behavior in the batch pipeline.

**Testing Scope**
- Valid text PDF still uses the existing fast path.
- Scan-like PDF with zero text triggers OCR fallback.
- Image files trigger OCR.
- Real `.doc` uses conversion, not `python-docx`.
- Pseudo-`.docx` is routed by actual content signature.

**Rollout Notes**
- Install LibreOffice on the batch execution machine.
- Add OCR dependency only after tests are in place.
- Validate on a small set of known failed samples before re-running large batches.
