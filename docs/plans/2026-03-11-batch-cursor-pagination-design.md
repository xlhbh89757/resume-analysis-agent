# Batch Cursor Pagination Design

## Goal

Make `scripts/run_batch_structuring.py` use the pending-list `cursor` as a real pagination mechanism while preserving the existing `--start-employee` and `--end-employee` range filters.

## Recommended Approach

Keep the existing CLI contract and add one optional argument:

- `--cursor`

The script should repeatedly call the pending-list API using `cursor`, aggregate filtered items, and stop when either:

1. enough items are collected to satisfy `--batch-size`
2. the API returns no `next_cursor`

This keeps backward compatibility and makes batch execution behave like true paginated consumption.

## Options Considered

### Option 1: Keep current range-only behavior

- Pros: no code change
- Cons: cursor is effectively unused, batching depends on guessing source-id ranges

Rejected.

### Option 2: Add cursor while keeping range filters

- Pros: backward compatible, operationally safer, easiest migration path
- Cons: slightly more script complexity

Recommended.

### Option 3: Remove range filters and use cursor only

- Pros: cleaner pagination model
- Cons: breaks current workflow and user habits

Rejected for now.

## Behavior

### Inputs

Keep:

- `--start-employee`
- `--end-employee`
- `--source-type`
- `--batch-size`
- `--dry-run`

Add:

- `--cursor`

### Selection Flow

1. Start from the provided `cursor` if present, otherwise from the first page.
2. Call `list_pending_resumes(source_type, cursor, limit=batch_size)`.
3. Filter each page by the preserved source-id range.
4. Keep collecting until `batch-size` is reached or `next_cursor` is empty.
5. Return `next_cursor` so the next invocation can continue naturally.

## Response Contract

The script result should include:

- `dry_run`
- `enqueued_count`
- `items`
- `next_cursor`
- `batch_id` when tasks are actually enqueued

## Testing Strategy

Add script tests that prove:

1. the script keeps requesting next pages when the first page does not fill the batch
2. a provided `cursor` is passed to the client on the first request
3. range filters still apply across pages
4. `next_cursor` is returned to callers

## Files To Change

- `scripts/run_batch_structuring.py`
- `tests/test_batch_scripts.py`
