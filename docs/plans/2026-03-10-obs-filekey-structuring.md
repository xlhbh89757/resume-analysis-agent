# OBS Filekey Structuring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch offline resume extraction from external temp-url fetching to internal OBS filekey signing while keeping synchronous source APIs backward compatible.

**Architecture:** Batch/list APIs will supply `source_type/source_id/filekey/resume_created_time`. Celery extract generates a fresh 15-minute URL from `filekey` via `OBSSigner` at execution time. Sync `structure-from-source` accepts optional `filekey`; if absent it falls back to old temp-url client behavior.

**Tech Stack:** FastAPI, SQLAlchemy, Celery, pytest, OBS presigned URL signing

---

### Task 1: Add failing tests for filekey-driven source client and signer flow
- Modify `tests/test_resume_source_client.py`
- Modify `tests/test_pipeline_flow.py`
- Modify `tests/test_batch_scripts.py`
- Modify `tests/test_temp_url_retry.py`
- Modify `tests/test_url_structuring_service.py`

### Task 2: Implement OBS signer config and source client filekey support
- Modify `src/core/config.py`
- Modify `.env.example`
- Modify `src/services/resume_source_client.py`
- Clean `src/obs/OBSSigner.py`
- Rewrite `src/obs/testObs.py` to config-driven demo

### Task 3: Wire filekey through URL structuring and Celery extract
- Modify `src/services/url_structuring_service.py`
- Modify `src/tasks/pipeline.py`
- Modify `src/tasks/analysis.py`
- Modify `src/api/schemas/resume.py`
- Modify `src/api/routes/resume.py`

### Task 4: Update batch scripts to use filekey payloads
- Modify `scripts/run_batch_structuring.py`
- Modify `scripts/retry_deadletter.py`

### Task 5: Full verification
- Run focused pytest
- Run full pytest
- Smoke check both CLI help commands
