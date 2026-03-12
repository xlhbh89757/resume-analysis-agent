# OCR and Legacy DOC Fallback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add OCR fallback for scanned/image resumes and correct parsing for legacy `.doc` files while preserving the existing text-first and LLM-first architecture.

**Architecture:** Keep `URLStructuringService` unchanged at the orchestration level. Extend `DocumentParser` to detect file signatures, route real file types correctly, convert legacy `.doc` with LibreOffice, and invoke OCR only when text extraction is missing or clearly low quality.

**Tech Stack:** Python, SQLAlchemy, python-docx, PyMuPDF, pdfplumber, RapidOCR, LibreOffice (`soffice`), pytest

---

### Task 1: Add failing parser tests for scanned PDFs, images, and legacy DOC

**Files:**
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/tests/test_document_parser_quality.py`
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/tests/test_document_parser_fallbacks.py`

**Step 1: Write failing tests for file signature routing**
- Add tests that verify real `.doc` files are not passed to `python-docx`.
- Add tests that verify pseudo-`.docx` files are routed by content signature.
- Add tests that verify image files trigger OCR path.

**Step 2: Run targeted tests to confirm failure**
Run: `pytest tests/test_document_parser_fallbacks.py -q -s -p no:cacheprovider`
Expected: FAIL because routing/OCR/conversion behavior does not exist yet.

**Step 3: Commit test-only checkpoint**
```bash
git add tests/test_document_parser_quality.py tests/test_document_parser_fallbacks.py
git commit -m "test: add parser fallback coverage"
```

### Task 2: Implement file signature detection and proper routing

**Files:**
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/src/services/document_parser.py`
- Test: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/tests/test_document_parser_fallbacks.py`

**Step 1: Add minimal file signature helpers**
- Detect PDF, DOCX, DOC, and common image signatures.
- Keep suffix as secondary signal only.

**Step 2: Route parser entry by actual content**
- Real PDF -> PDF path
- Real DOCX -> DOCX path
- Real DOC -> DOC conversion path
- Image -> OCR path
- Unknown -> explicit unsupported-file error

**Step 3: Run targeted tests**
Run: `pytest tests/test_document_parser_fallbacks.py -q -s -p no:cacheprovider`
Expected: routing tests pass, OCR/conversion tests still fail.

**Step 4: Commit**
```bash
git add src/services/document_parser.py tests/test_document_parser_fallbacks.py
git commit -m "feat: detect resume file types by content signature"
```

### Task 3: Add OCR fallback for scanned PDFs and images

**Files:**
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/src/services/document_parser.py`
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/pyproject.toml`
- Test: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/tests/test_document_parser_fallbacks.py`

**Step 1: Add OCR abstraction with graceful dependency check**
- If OCR dependency is missing, raise a clear runtime error only when OCR is needed.

**Step 2: Implement image OCR path**
- Read image file and extract text.

**Step 3: Implement PDF OCR fallback**
- Convert PDF pages to images.
- Run OCR when text extraction returns empty or low-quality text.

**Step 4: Run targeted tests**
Run: `pytest tests/test_document_parser_fallbacks.py tests/test_document_parser_quality.py -q -s -p no:cacheprovider`
Expected: OCR fallback tests pass.

**Step 5: Commit**
```bash
git add src/services/document_parser.py pyproject.toml tests/test_document_parser_fallbacks.py tests/test_document_parser_quality.py
git commit -m "feat: add OCR fallback for scanned resumes"
```

### Task 4: Add LibreOffice conversion path for legacy DOC

**Files:**
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/src/services/document_parser.py`
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/src/core/config.py`
- Modify: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/.env.example`
- Test: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/tests/test_document_parser_fallbacks.py`

**Step 1: Add configurable `soffice` path**
- Read from settings, default to common Windows install path.

**Step 2: Implement `.doc -> pdf` conversion helper**
- Use `soffice --headless --convert-to pdf --outdir ...`
- Re-enter the PDF parse flow after conversion.

**Step 3: Handle conversion failure explicitly**
- Raise a dedicated conversion error message.

**Step 4: Run targeted tests**
Run: `pytest tests/test_document_parser_fallbacks.py -q -s -p no:cacheprovider`
Expected: DOC conversion routing tests pass.

**Step 5: Commit**
```bash
git add src/services/document_parser.py src/core/config.py .env.example tests/test_document_parser_fallbacks.py
git commit -m "feat: add legacy doc conversion fallback"
```

### Task 5: Verify end-to-end parser behavior on real failed samples

**Files:**
- No code changes required unless failures expose gaps.

**Step 1: Run targeted parser checks on known failed samples**
- Use `source_id=12496` sample for scanned PDF.
- Use at least one known dead `.doc` sample.

**Step 2: Confirm expected outcomes**
- Scanned PDF now produces non-empty text.
- Real `.doc` no longer goes through `python-docx` directly.

**Step 3: Run full test suite**
Run: `pytest -q -s -p no:cacheprovider`
Expected: full suite passes.

**Step 4: Commit**
```bash
git add -A
git commit -m "fix: improve resume parsing for scanned pdf and doc files"
```
