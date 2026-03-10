# Pending Resumes API Design

- Goal: add `GET /api/v1/resumes/pending` in this project and return the unified batch input fields: `source_type`, `source_id`, `resume_created_time`, and `filekey`.
- Query: use the provided SQL as the data source, then filter by `source_type` in the service layer and apply a simple cursor based on `source_id`.
- Contract: return `{ items, next_cursor }` and keep the same shape as `ResumeSourceClient.list_pending_resumes(...)` so the batch scripts and Celery pipeline do not need contract changes.
- Error handling: return an empty list for `entrant` for now; let framework-level database errors bubble up; keep the interface small and predictable.
- Testing: cover row mapping, limit-plus-one pagination, `next_cursor` calculation, and the HTTP response shape.
