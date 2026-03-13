# Docker Deployment Design for Resume API

**Goal:** Deploy the resume single-file structuring API on a Linux server using Docker, while keeping MySQL and Redis as external services.

**Scope**
- Provide production-ready single-resume API service.
- Package API runtime, OCR runtime, and LibreOffice into the application image.
- Use an Nginx container for reverse proxy and request shaping.
- Do not containerize MySQL or Redis.

**Recommended Topology**
1. `resume-api` container
- Runs FastAPI/Uvicorn.
- Includes Python runtime, project code, OCR dependency, LibreOffice, and required system libraries.
- Connects to external MySQL, external Redis, OBS, and DeepSeek API.

2. `nginx` container
- Exposes `80/443`.
- Proxies to `resume-api`.
- Handles HTTPS termination, body-size control, timeout tuning, and optional token/IP filtering.

**Why This Topology**
- Keeps deployment minimal and aligned with the current use case: single-resume synchronous structuring.
- Avoids adding containerized data services that already exist externally.
- Preserves future compatibility with batch/Celery if Redis is needed later.

**Application Image Requirements**
- Python 3.10 runtime.
- Project source code.
- Python dependencies from `pyproject.toml`.
- LibreOffice installed in the image.
- OCR dependency installed and usable at runtime.
- Font packages and common image/document runtime dependencies.

**Configuration Model**
Use environment variables only. Required production variables include:
- `DATABASE_URL`
- `LLM_PROVIDER`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OBS_ACCESS_KEY`
- `OBS_SECRET_KEY`
- `OBS_BUCKET`
- `OBS_HOST`
- `OBS_URL_EXPIRE_SECONDS`
- `LIBREOFFICE_PATH=/usr/bin/soffice`
- optional `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

**Security Requirements**
- Do not expose Uvicorn directly to the internet.
- Put Nginx in front of the API.
- Add at least one of:
  - token authentication
  - gateway authentication
  - IP allowlist
- Use HTTPS.
- Set request size limits and proxy timeouts explicitly.

**Operational Notes**
- Build the image once and promote the same artifact to production.
- Persist logs through Docker logging driver or external log collection.
- Keep batch and sync API concerns separate. For this deployment, API is primary.
- If Celery batch is needed later, add worker containers separately instead of overloading the API container.

**Validation Before Go-Live**
Run real-file smoke tests for:
- normal PDF
- scanned PDF
- `.doc`
- `.docx`
- `force-reparse`

**Expected Deliverables**
- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml` for `resume-api + nginx`
- `nginx.conf`
- deployment runbook
