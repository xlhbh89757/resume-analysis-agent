# Pending Resumes API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** add a unified pending resumes API in this project for the offline batch pipeline.

**Architecture:** add one query service that runs raw SQL and normalizes pagination output. The FastAPI route only validates input and returns the existing `{ items, next_cursor }` contract.

**Tech Stack:** FastAPI, SQLAlchemy Session, raw SQL, pytest

---

### Task 1: Service Red Test
- Files: `tests/test_pending_resume_service.py`
- Cover row mapping, `limit + 1` pagination, and `next_cursor` calculation.

### Task 2: Route Red Test
- Files: `tests/test_resume_pending_api.py`
- Cover `GET /api/v1/resumes/pending` response shape and parameter passthrough.

### Task 3: Minimal Implementation
- Files: `src/services/pending_resume_service.py`, `src/api/schemas/resume.py`, `src/api/routes/resume.py`
- Implement the query service, response schema, and route.

### Task 4: Regression
- Run: `pytest tests/test_pending_resume_service.py tests/test_resume_pending_api.py -q -s -p no:cacheprovider`
- Then run the full suite: `pytest -q -s -p no:cacheprovider`
