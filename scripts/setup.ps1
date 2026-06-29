# One-time local setup for travel-planner-api (Windows PowerShell)
# Usage: .\scripts\setup.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> travel-planner-api setup" -ForegroundColor Cyan

# .env
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example"
} else {
    Write-Host ".env already exists — skipping"
}

# data dirs
New-Item -ItemType Directory -Force -Path "data\uploads" | Out-Null

# Python deps
Write-Host "==> Installing Python dependencies..."
python -m pip install -e ".[dev]"

# Database + seed
Write-Host "==> Seeding demo data..."
python scripts/seed_demo.py

# Tests
Write-Host "==> Running tests..."
python -m pytest tests/ -q

Write-Host ""
Write-Host "Setup complete. Start the API with:" -ForegroundColor Green
Write-Host "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host ""
Write-Host "Mobile app URL (set in travel-planner-mobile/.env):" -ForegroundColor Green
$lan = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
    $_.InterfaceAlias -notmatch 'Loopback' -and $_.IPAddress -notmatch '^169\.'
} | Select-Object -First 1).IPAddress
if ($lan) {
    Write-Host "  EXPO_PUBLIC_API_BASE_URL=http://${lan}:8000/v1"
}
