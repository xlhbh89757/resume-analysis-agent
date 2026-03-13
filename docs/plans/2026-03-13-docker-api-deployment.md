# Docker API Deployment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Docker-based Linux deployment for the single-resume structuring API, using external MySQL/Redis and packaging OCR plus LibreOffice inside the application image.

**Architecture:** The deployment uses one application container and one Nginx container. The application image contains Python dependencies, OCR runtime, and LibreOffice so scanned PDFs, images, `.doc`, and `.docx` can all be processed inside the container without host-specific manual setup.

**Tech Stack:** Docker, Docker Compose, FastAPI, Uvicorn, Nginx, LibreOffice, RapidOCR, Python 3.10

---

### Task 1: Add Docker build artifacts for the API container

**Files:**
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/Dockerfile`
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/.dockerignore`

**Step 1: Write the failing smoke expectation in plan comments**
- The image must contain:
  - Python runtime
  - project dependencies
  - LibreOffice
  - OCR dependency runtime
  - `soffice` available at `/usr/bin/soffice` or discovered equivalent

**Step 2: Build a minimal Linux image definition**
- Base image: Python 3.10 slim
- Install system packages for LibreOffice and image processing
- Install project dependencies
- Copy source code
- Set `LIBREOFFICE_PATH=/usr/bin/soffice`

**Step 3: Add `.dockerignore`**
- Exclude `.venv`, `.git`, local temp files, test caches, and uploads

**Step 4: Verify image build locally or on Linux target**
Run: `docker build -t resume-api:local .`
Expected: image builds successfully

**Step 5: Commit**
```bash
git add Dockerfile .dockerignore
git commit -m "build: add api docker image"
```

### Task 2: Add Nginx reverse proxy configuration

**Files:**
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/deploy/nginx/nginx.conf`

**Step 1: Define reverse proxy settings**
- Proxy to `resume-api:8000`
- Set `client_max_body_size`
- Set upstream/read/send timeouts for long-running resume parsing
- Preserve request headers and real IP headers

**Step 2: Add health-oriented routing**
- Route `/` and `/api/` to app
- Keep config minimal; no unrelated gateway logic

**Step 3: Validate config syntax in containerized Nginx**
Run: `docker run --rm -v $(pwd)/deploy/nginx/nginx.conf:/etc/nginx/nginx.conf:ro nginx:stable nginx -t`
Expected: syntax is ok

**Step 4: Commit**
```bash
git add deploy/nginx/nginx.conf
git commit -m "ops: add nginx reverse proxy config"
```

### Task 3: Add docker-compose for production-style local deployment

**Files:**
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/docker-compose.api.yml`

**Step 1: Define services**
- `resume-api`
- `nginx`

**Step 2: Inject environment variables**
- Use `.env`
- Do not define MySQL/Redis containers
- Mount only what is necessary

**Step 3: Expose ports**
- `nginx` exposes `80` (and `443` later if TLS certs are managed locally)
- `resume-api` remains internal to compose network

**Step 4: Verify compose syntax**
Run: `docker compose -f docker-compose.api.yml config`
Expected: configuration resolves without errors

**Step 5: Commit**
```bash
git add docker-compose.api.yml
git commit -m "ops: add docker compose deployment for api"
```

### Task 4: Add deployment runbook for Linux server

**Files:**
- Create: `e:/antigravityWork/agent/resume-agent/.worktrees/resume-url-batch-structuring/docs/runbooks/docker-api-deployment.md`

**Step 1: Document prerequisites**
- Docker
- Docker Compose plugin
- external MySQL/Redis reachability
- OBS/DeepSeek connectivity

**Step 2: Document environment variables**
- Include required `.env` keys
- Include `LIBREOFFICE_PATH=/usr/bin/soffice`

**Step 3: Document startup commands**
- build image
- start compose
- inspect logs
- stop/restart services

**Step 4: Document smoke tests**
- `structure-from-source`
- scanned PDF
- `.doc`
- `force-reparse`

**Step 5: Commit**
```bash
git add docs/runbooks/docker-api-deployment.md
git commit -m "docs: add docker api deployment runbook"
```

### Task 5: Verify deployment artifacts

**Files:**
- No new files; verify existing work

**Step 1: Run targeted verification**
Run:
- `docker build -t resume-api:local .`
- `docker compose -f docker-compose.api.yml config`

**Step 2: Smoke check the app container assumptions**
- verify `soffice --version`
- verify app starts with `.env`

**Step 3: Run test suite again**
Run: `pytest -q -s -p no:cacheprovider`
Expected: all tests still pass

**Step 4: Commit final integration checkpoint**
```bash
git add -A
git commit -m "ops: finalize docker deployment setup"
```
