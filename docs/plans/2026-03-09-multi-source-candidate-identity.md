# Multi-Source Candidate Identity Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add multi-source business identifiers to candidates and upgrade resume structuring flows from `employee_id`-only to `source_type + source_id` while preserving backward compatibility.

**Architecture:** Candidate persistence becomes source-aware and deduplicates by source IDs first, then phone/email. API, source client, URL structuring service, and Celery pipeline all share a generic source model, while `structure-from-employee` remains a compatibility wrapper.

**Tech Stack:** FastAPI, SQLAlchemy, MySQL, Celery, Redis, pytest

---

@superpowers:test-driven-development
@superpowers:verification-before-completion

### Task 1: Add source identifier fields to candidate and governance models

**Files:**
- Modify: `src/models/candidate.py`
- Modify: `src/models/resume_batch.py`
- Modify: `src/models/__init__.py`
- Modify: `scripts/init_db.py`
- Create: `scripts/migrate_add_candidate_source_ids.py`
- Test: `tests/test_resume_batch_models.py`

**Step 1: Write the failing test**
- Extend model tests to assert `Candidate` accepts `employee_id / entrant_id / submit_candidate_id`.
- Extend governance tests to assert `ResumeStructTask/ResumeStructDeadletter` store `source_type/source_id`.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_resume_batch_models.py -q`
Expected: FAIL because fields are missing.

**Step 3: Write minimal implementation**
- Add indexed nullable columns to `Candidate`.
- Replace governance `employee_id` columns with `source_type/source_id`.
- Add migration script for existing MySQL tables.
- Keep Chinese comments on new schema fields.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_resume_batch_models.py -q`
Expected: PASS

### Task 2: Generalize source client and API schema

**Files:**
- Modify: `src/services/resume_source_client.py`
- Modify: `src/api/schemas/resume.py`
- Test: `tests/test_resume_source_client.py`

**Step 1: Write the failing test**
- Add tests for `get_temp_url(source_type="submit_candidate", source_id="S001")`.
- Add tests for `list_pending_resumes(source_type=...)` response shape.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_resume_source_client.py -q`
Expected: FAIL because client only supports employee endpoints.

**Step 3: Write minimal implementation**
- Introduce `source_type/source_id` API in client.
- Keep `get_temp_url(employee_id)` compatibility wrapper if useful.
- Add `SourceResumeStructureRequest` schema and richer response fields.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_resume_source_client.py -q`
Expected: PASS

### Task 3: Implement source-aware candidate matching and persistence

**Files:**
- Modify: `src/services/persist_service.py`
- Modify: `src/services/url_structuring_service.py`
- Test: `tests/test_persist_service.py`
- Test: `tests/test_url_structuring_service.py`

**Step 1: Write the failing test**
- Add test that existing candidate is found by `submit_candidate_id`.
- Add test that existing candidate is found by `phone/email` and backfilled with new source ID.
- Add test that `structure_from_source` persists `submit_candidate_id` for report candidates.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_persist_service.py tests/test_url_structuring_service.py -q`
Expected: FAIL because persistence always creates a new candidate and service only supports employee source.

**Step 3: Write minimal implementation**
- Add generic source payload handling.
- Implement candidate locator order: source IDs -> phone -> email.
- Backfill source identifier fields on matched candidate.
- Add `structure_from_source` and compatibility wrappers.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_persist_service.py tests/test_url_structuring_service.py -q`
Expected: PASS

### Task 4: Upgrade API and Celery pipeline to generic sources

**Files:**
- Modify: `src/api/routes/resume.py`
- Modify: `src/tasks/pipeline.py`
- Modify: `src/tasks/analysis.py`
- Modify: `scripts/run_batch_structuring.py`
- Modify: `scripts/retry_deadletter.py`
- Test: `tests/test_resume_url_api.py`
- Test: `tests/test_pipeline_flow.py`
- Test: `tests/test_temp_url_retry.py`
- Test: `tests/test_batch_scripts.py`

**Step 1: Write the failing test**
- Add `/structure-from-source` endpoint test.
- Update pipeline tests to use `source_type/source_id`.
- Update temp URL retry test to refresh by generic source.
- Update batch script tests to accept `--source-type`.

**Step 2: Run test to verify it fails**
Run: `pytest tests/test_resume_url_api.py tests/test_pipeline_flow.py tests/test_temp_url_retry.py tests/test_batch_scripts.py -q`
Expected: FAIL because API/tasks/scripts still use `employee_id`.

**Step 3: Write minimal implementation**
- Add generic source endpoint.
- Keep `structure-from-employee` wrapper.
- Make pipeline payloads and analysis tasks generic.
- Make batch scripts operate on one `source_type` per run.

**Step 4: Run test to verify it passes**
Run: `pytest tests/test_resume_url_api.py tests/test_pipeline_flow.py tests/test_temp_url_retry.py tests/test_batch_scripts.py -q`
Expected: PASS

### Task 5: Full regression

**Files:**
- Verify only

**Step 1: Run full test suite**
Run: `pytest -q -s -p no:cacheprovider`
Expected: PASS

**Step 2: Smoke-check CLI entry points**
Run:
- `python scripts/run_batch_structuring.py --help`
- `python scripts/retry_deadletter.py --help`
Expected: both commands print usage successfully.
