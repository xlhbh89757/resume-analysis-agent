$ErrorActionPreference = "Stop"

Set-Location "E:\antigravityWork\agent\resume-agent"

$env:DATABASE_URL = "mysql+pymysql://root:root@localhost:3306/resume_agent?charset=utf8mb4"
$env:REDIS_URL = "redis://localhost:6379/0"
$env:QDRANT_URL = "http://localhost:6333"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"

$process = Start-Process -FilePath "E:\antigravityWork\agent\resume-agent\.venv\Scripts\pythonw.exe" `
    -ArgumentList "-m","uvicorn","src.api.main:app","--host","127.0.0.1","--port","8000" `
    -WorkingDirectory "E:\antigravityWork\agent\resume-agent" `
    -PassThru

$process.Id | Set-Content "E:\antigravityWork\agent\resume-agent\.tmp\resume_agent.pid"
