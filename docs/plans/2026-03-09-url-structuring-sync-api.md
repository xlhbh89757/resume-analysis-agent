# URL Structuring Sync API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add synchronous resume structuring APIs for `employee_id + resume_created_time` and direct `resume_url`, backed by one shared URL download and parsing service.

**Architecture:** Introduce a shared async service that downloads resume files from a URL into a temporary file, parses text, calls the LLM extractor, and persists the result through the existing idempotent persistence service. Both new API endpoints and the later Celery extract task will reuse this service so URL handling only exists in one place.

**Tech Stack:** FastAPI, httpx, tempfile/pathlib, DocumentParser, LLMAnalysisService, SQLAlchemy, pytest

---

@superpowers:test-driven-development
@superpowers:verification-before-completion

### Task 1: Add shared URL structuring service

**Files:**
- Create: `src/services/url_structuring_service.py`
- Test: `tests/test_url_structuring_service.py`

**Step 1: Write the failing test**
```python
def test_structure_from_url_downloads_parses_and_persists():
    ...
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_url_structuring_service.py -q -s -p no:cacheprovider`
Expected: FAIL with missing service.

**Step 3: Write minimal implementation**
- Download URL to a temporary file.
- Parse the local file with `DocumentParser`.
- Extract structured info with `LLMAnalysisService`.
- Persist through `PersistService`.
- Return candidate/task/result summary.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_url_structuring_service.py -q -s -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**
```bash
git add src/services/url_structuring_service.py tests/test_url_structuring_service.py
git commit -m "feat: 新增URL简历结构化服务"
```

### Task 2: Add synchronous API endpoints

**Files:**
- Modify: `src/api/routes/resume.py`
- Test: `tests/test_resume_url_api.py`

**Step 1: Write the failing test**
```python
def test_structure_resume_from_url_endpoint_returns_candidate_id():
    ...
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_resume_url_api.py -q -s -p no:cacheprovider`
Expected: FAIL with missing route.

**Step 3: Write minimal implementation**
- Add `/resumes/structure-from-url`
- Add `/resumes/structure-from-employee`
- Reuse the shared URL structuring service
- Keep responses synchronous and explicit

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_resume_url_api.py -q -s -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**
```bash
git add src/api/routes/resume.py tests/test_resume_url_api.py
git commit -m "feat: 新增URL简历结构化接口"
```

### Task 3: Wire extract task to shared URL service entry points

**Files:**
- Modify: `src/tasks/analysis.py`
- Modify: `src/tasks/pipeline.py`
- Test: `tests/test_pipeline_flow.py`

**Step 1: Write the failing test**
```python
def test_extract_payload_can_carry_download_context():
    ...
```

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_pipeline_flow.py -q -s -p no:cacheprovider`
Expected: FAIL with missing shared-service payload fields.

**Step 3: Write minimal implementation**
- Keep queue payload stable.
- Add helper payload builders needed by shared URL service.
- Prepare extract task to call the shared service in later batch flow.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_pipeline_flow.py -q -s -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**
```bash
git add src/tasks/analysis.py src/tasks/pipeline.py tests/test_pipeline_flow.py
git commit -m "refactor: 统一URL结构化任务入口"
```