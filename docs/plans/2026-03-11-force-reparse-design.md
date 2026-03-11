# Force Reparse Design

## Goal

Add a force-reparse capability for resumes that already have a successful structured result but need to be re-downloaded, re-parsed, and re-persisted because the original result quality is poor.

## Recommended Approach

Use a new synchronous API endpoint that reuses the existing source-based structuring flow and adds a `force_reparse` flag through the service and persistence layers.

This keeps the existing pipeline intact, avoids risky manual deletes, and limits changes to a small number of files.

## Options Considered

### Option 1: Delete data and rerun

- Pros: minimal implementation
- Cons: high operational risk, weak auditability, easy to delete the wrong related rows

Rejected.

### Option 2: Force-reparse API that reuses the existing task

- Pros: smallest change set, fast to deliver, matches current idempotency model
- Cons: task history is reused rather than split into separate rerun records

Recommended.

### Option 3: Force-reparse API that creates a dedicated rerun task

- Pros: best audit history
- Cons: larger model and migration changes, unnecessary for the current phase

Deferred.

## API Design

### Endpoint

- `POST /api/v1/resumes/force-reparse`

### Request Body

```json
{
  "source_type": "employee",
  "source_id": "1528",
  "resume_created_time": "2025-02-27 10:25:52",
  "filekey": "/employee/2025-02-27/202545P2RAPP0829.pdf",
  "reason": "low_quality_resume_text"
}
```

### Response Body

```json
{
  "status": "success",
  "candidate_id": 26,
  "idempotency_key": "employee:1528:2025-02-27 10:25:52",
  "force_reparse": true,
  "source_type": "employee",
  "source_id": "1528",
  "resume_created_time": "2025-02-27 10:25:52",
  "resume_url": "https://...",
  "structured_resume": {}
}
```

## Data Flow

1. API receives `source_type`, `source_id`, `resume_created_time`, optional `filekey`, and optional `reason`.
2. `URLStructuringService.structure_from_source(...)` is called with `force_reparse=True`.
3. The service resolves the resume URL, downloads the file, parses text, and extracts structured data with the LLM.
4. `PersistService.persist_structured_resume(...)` receives `force_reparse=True`.
5. If the existing task is already `success`, persistence no longer returns `skipped`; it updates the task and overwrites the candidate data.
6. On failure, the existing deadletter path remains in effect.

## Persistence Rules

### Existing Behavior

- Same `source_type + source_id + resume_created_time`
- Existing successful task returns `skipped`

### New Behavior

- If `force_reparse=False`, keep the existing skip behavior.
- If `force_reparse=True`, allow the successful task to be reprocessed.

### Overwrite Scope

The following candidate data is overwritten:

- `resume_text`
- base fields such as `name`, `email`, `phone`, `education_level`, `years_of_experience`, `current_position`, `summary`
- `work_experiences`
- `project_experiences`
- `skills`

This matches the current `apply_structured_resume(...)` overwrite model.

## Task Handling

Reuse the existing `ResumeStructTask` row identified by the idempotency key.

When force-reparse is triggered:

- set `status` to `running`
- increment `attempt_count`
- clear old `error_code` and `error_message`
- update `started_at`
- on success, set `finished_at` and `status=success`
- on failure, use the existing deadletter behavior

No schema change is required for this version.

## Error Handling

Keep the current behavior:

- download failures -> `E_DOWNLOAD`
- parse failures -> `E_PARSE`
- extract-stage unexpected failures -> `E_EXTRACT`
- failed tasks go to `resume_struct_deadletters`

The force-reparse endpoint must not bypass governance.

## Testing Strategy

Add tests for:

1. existing successful task remains `skipped` in the normal path
2. existing successful task is reprocessed when `force_reparse=True`
3. candidate details are overwritten on force-reparse
4. `attempt_count` increments during force-reparse
5. API request reaches the service with `force_reparse=True`

## Files Expected To Change

- `src/api/schemas/resume.py`
- `src/api/routes/resume.py`
- `src/services/url_structuring_service.py`
- `src/services/persist_service.py`
- `tests/test_persist_service.py`
- `tests/test_resume_url_api.py`
- optional: targeted new tests if coverage is clearer that way
