# Docker API Deployment

## Scope

Deploy the single-resume structuring API on Linux with:

1. `resume-api` container
2. `nginx` reverse proxy container

External dependencies remain outside Docker:

1. MySQL
2. Redis
3. OBS
4. DeepSeek API

## Prerequisites

1. Linux server with Docker and Docker Compose plugin
2. External MySQL reachable from the server
3. External Redis reachable from the server if batch/Celery is still needed
4. OBS and DeepSeek API reachable from the server

## Required environment file

Create:

```text
deploy/docker/.env.api
```

You can copy from:

```text
deploy/docker/.env.api.example
```

At minimum:

```env
DATABASE_URL=mysql+pymysql://...
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

OBS_ACCESS_KEY=...
OBS_SECRET_KEY=...
OBS_BUCKET=...
OBS_HOST=...
OBS_URL_EXPIRE_SECONDS=3600

```

If batch/Celery is still needed later, also keep:

```env
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...
CELERY_RESULT_BACKEND=redis://...
```

## Build

```bash
docker build -t resume-api:local .
```

## Start

```bash
cp deploy/docker/.env.api.example deploy/docker/.env.api
docker compose --env-file deploy/docker/.env.api -f docker-compose.api.yml up -d --build
```

## Check

```bash
docker compose --env-file deploy/docker/.env.api -f docker-compose.api.yml ps
docker compose --env-file deploy/docker/.env.api -f docker-compose.api.yml logs -f resume-api
docker compose --env-file deploy/docker/.env.api -f docker-compose.api.yml logs -f nginx
```

## Smoke Tests

1. Open Swagger:

```text
http://<server-ip>/docs
```

2. Verify single-resume APIs:

- `POST /api/v1/resumes/structure-from-source`
- `POST /api/v1/resumes/structure-from-url`
- `POST /api/v1/resumes/force-reparse`

3. Verify these file types:

- normal PDF
- scanned PDF
- `.doc`
- `.docx`

## Stop

```bash
docker compose --env-file deploy/docker/.env.api -f docker-compose.api.yml down
```
