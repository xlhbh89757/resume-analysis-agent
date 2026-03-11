# Force Reparse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a synchronous force-reparse API that bypasses the normal success-skip behavior and overwrites an existing structured resume result for the same source key.

**Architecture:** Extend the existing source-based structuring path with a `force_reparse` flag. Reuse the existing download, parse, extract, persist, and deadletter flow instead of introducing a new task model.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest

---

### Task 1: Add failing tests for persistence force-reparse behavior

**Files:**
- Modify: `tests/test_persist_service.py`
- Modify: `src/services/persist_service.py`

**Step 1: Write the failing test**

Add tests that prove:
- a successful existing task normally returns `skipped`
- the same task with `force_reparse=True` returns `success`
- `attempt_count` increments and candidate fields are overwritten

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_persist_service.py -q -s -p no:cacheprovider
```

Expected: FAIL because `force_reparse` is not implemented.

**Step 3: Write minimal implementation**

Update `PersistService.persist_structured_resume(...)` to honor `force_reparse`.

**Step 4: Run test to verify it passes**

Run the same test command and confirm PASS.

**Step 5: Commit**

```bash
git add tests/test_persist_service.py src/services/persist_service.py
git commit -m "feat: add persist force reparse support"
```

### Task 2: Add failing tests for service and API force-reparse behavior

**Files:**
- Modify: `tests/test_resume_url_api.py`
- Modify: `src/api/schemas/resume.py`
- Modify: `src/api/routes/resume.py`
- Modify: `src/services/url_structuring_service.py`

**Step 1: Write the failing test**

Add tests that prove:
- `POST /api/v1/resumes/force-reparse` exists
- it forwards `force_reparse=True`
- the response contains `force_reparse=true`

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_resume_url_api.py -q -s -p no:cacheprovider
```

Expected: FAIL because the endpoint and schema do not exist.

**Step 3: Write minimal implementation**

Add the request schema, route, and URL structuring service support.

**Step 4: Run test to verify it passes**

Run the same test command and confirm PASS.

**Step 5: Commit**

```bash
git add tests/test_resume_url_api.py src/api/schemas/resume.py src/api/routes/resume.py src/services/url_structuring_service.py
git commit -m "feat: add force reparse api"
```

### Task 3: Run regression verification

**Files:**
- Modify: none
- Test: `tests/test_persist_service.py`
- Test: `tests/test_resume_url_api.py`

**Step 1: Run targeted tests**

```bash
pytest tests/test_persist_service.py tests/test_resume_url_api.py -q -s -p no:cacheprovider
```

Expected: PASS

**Step 2: Run full test suite**

```bash
pytest -q -s -p no:cacheprovider
```

Expected: PASS

**Step 3: Review changed files**

```bash
git diff --stat
```

Expected: only force-reparse related files changed.

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add resume force reparse flow"
```
