# Batch Total Limit Design

## Goal

Add an optional `--total-limit` mode to `scripts/run_batch_structuring.py` so one command can continuously create multiple batches until a target number of resumes has been enqueued.

## Recommended Approach

Keep the current single-batch behavior as the default.

Add:

- `--total-limit`

If it is not provided, preserve the current behavior exactly.

If it is provided, the script should:

1. keep using cursor pagination
2. create repeated batches of size `--batch-size`
3. accumulate the number of actually enqueued tasks
4. stop when:
   - accumulated count reaches `total-limit`
   - or pending-list pagination ends

## Options Considered

### Option 1: Replace current behavior entirely

- Pros: simpler long-term interface
- Cons: breaks current testing flow and existing usage

Rejected.

### Option 2: Add optional `--total-limit` and keep current behavior

- Pros: fully backward compatible, safer rollout, supports both testing and bulk execution
- Cons: more script branching

Recommended.

### Option 3: Add a separate script for full-run mode

- Pros: no branching in the current script
- Cons: duplicated logic and more maintenance cost

Rejected.

## Behavior

### Existing Mode

Without `--total-limit`:

- fetch enough items for one batch
- create one `resume_struct_batches` row
- enqueue one batch

### New Mode

With `--total-limit`:

- repeatedly fetch the next batch using `next_cursor`
- create one batch at a time
- enqueue it
- continue until the cumulative count reaches `total-limit`

### Example

```bash
python scripts/run_batch_structuring.py \
  --start-employee 000000 \
  --end-employee 999999 \
  --source-type employee \
  --batch-size 100 \
  --total-limit 6624
```

Expected behavior:

- create around 67 batches
- each batch targets up to 100 resumes
- stop after enqueuing 6624 resumes or when there is no more data

## Result Contract

Return a summary that includes:

- `dry_run`
- `batch_size`
- `total_limit`
- `requested_batches`
- `enqueued_count`
- `batches`
- `next_cursor`

For the old single-batch mode, keep the old fields and add the new summary fields only if convenient.

## Testing Strategy

Add tests that prove:

1. single-batch mode is unchanged when `--total-limit` is absent
2. multi-batch mode creates multiple batches until the limit is reached
3. cursor is advanced across successive batches
4. actual enqueued count, not selected count, controls the loop

## Files To Change

- `scripts/run_batch_structuring.py`
- `tests/test_batch_scripts.py`
