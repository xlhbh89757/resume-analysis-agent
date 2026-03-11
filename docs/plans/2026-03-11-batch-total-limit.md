# Batch Total Limit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an optional `--total-limit` mode so one command can create and enqueue multiple cursor-driven batches until a target number of resumes has been dispatched.

**Architecture:** Preserve the current single-batch flow when `--total-limit` is absent. When it is present, loop over the existing cursor-driven selection logic, create one batch per loop, and keep advancing `next_cursor` until the cumulative enqueue count hits the requested total.

**Tech Stack:** Python, argparse, pytest, SQLAlchemy

---

### Task 1: Add failing tests for multi-batch dispatch

**Files:**
- Modify: `tests/test_batch_scripts.py`
- Modify: `scripts/run_batch_structuring.py`

**Step 1: Write the failing test**

Add tests that prove:
- `--total-limit` creates multiple batches
- each batch respects `--batch-size`
- the loop stops once the total target is reached
- the returned summary includes created batch ids and `next_cursor`

**Step 2: Run test to verify it fails**

Run:

```bash
pytest tests/test_batch_scripts.py -q -s -p no:cacheprovider
```

Expected: FAIL because the script only creates a single batch today.

**Step 3: Write minimal implementation**

Add the loop and preserve single-batch behavior.

**Step 4: Run test to verify it passes**

Run the same command and confirm PASS.

**Step 5: Commit**

```bash
git add tests/test_batch_scripts.py scripts/run_batch_structuring.py
git commit -m "feat: add total-limit batch dispatch mode"
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
git commit -m "feat: support multi-batch total limit dispatch"
```
