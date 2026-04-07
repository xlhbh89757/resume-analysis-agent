$ErrorActionPreference = "Stop"

Set-Location "E:\antigravityWork\agent\resume-agent"

$env:DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/resume_agent?charset=utf8mb4"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:QDRANT_URL = "http://localhost:6333"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

& "E:\antigravityWork\agent\resume-agent\.venv\Scripts\python.exe" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
