# Batch Cursor Pagination Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make batch dispatch use pending-list cursor pagination while preserving the current range filter parameters.

**Architecture:** Extend `run_batch_structuring.py` with an optional `--cursor`, fetch pages incrementally, apply the existing source-id range filter to each page, and stop once enough items are selected or pagination ends. Return `next_cursor` in both dry-run and enqueue paths.

**Tech Stack:** Python, argparse, pytest, SQLAlchemy

---

### Task 1: Add failing tests for paginated selection

**Files:**
- Modify: `tests/test_batch_scripts.py`
- Modify: `scripts/run_batch_structuring.py`

**Step 1: Write the failing test**

Add tests that prove:
- the script fetches multiple pages until `batch-size` is satisfied
- the provided `--cursor` is used on the first API call
- `next_cursor` is returned

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_batch_scripts.py -q -s -p no:cacheprovider
```

Expected: FAIL because the current script only fetches one page effectively.

**Step 3: Write minimal implementation**

Update the script to loop over pages and accumulate filtered items.

**Step 4: Run test to verify it passes**

Run the same test command and confirm PASS.

**Step 5: Commit**

```bash
git add tests/test_batch_scripts.py scripts/run_batch_structuring.py
git commit -m "feat: add cursor pagination to batch script"
```

### Task 2: Run regression verification

**Files:**
- Modify: none

**Step 1: Run targeted tests**

```bash
pytest tests/test_batch_scripts.py -q -s -p no:cacheprovider
```

Expected: PASS

**Step 2: Run full test suite**

```bash
pytest -q -s -p no:cacheprovider
```

Expected: PASS

**Step 3: Commit**

```bash
git add .
git commit -m "feat: support cursor-based batch pagination"
```
