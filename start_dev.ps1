$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Resume Agent Development Environment..." -ForegroundColor Green

# 1. Check Docker
Write-Host "`n📦 Checking Docker status..."
try {
    docker info > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker is not running"
    }
    Write-Host "   Docker is running." -ForegroundColor Gray
}
catch {
    Write-Host "❌ Docker is not running! Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# 2. Start Services
Write-Host "`n🐳 Starting infrastructure services (Postgres, Redis, Qdrant)..."
try {
    docker-compose up -d
    Write-Host "   Services started." -ForegroundColor Gray
}
catch {
    Write-Host "❌ Failed to start docker-compose services." -ForegroundColor Red
    exit 1
}

# 3. Initialize Database
Write-Host "`n🛠️  Initializing database..."
try {
    # Wait a bit for DB to be ready
    Start-Sleep -Seconds 5
    python scripts/init_db.py
}
catch {
    Write-Host "⚠️  Database initialization warning (might be already initialized or connecting too soon)." -ForegroundColor Yellow
}

# 4. Start API Server
Write-Host "`n🔥 Starting API Server..."
Write-Host "   Docs will be available at: http://localhost:8000/docs" -ForegroundColor Cyan
python -m uvicorn src.api.main:app --reload --port 8000
