# PowerShell script to check Docker status
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Checking Docker Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not found"
    }
    Write-Host "✓ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker Desktop first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if Docker is running
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker Desktop is running" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now run:" -ForegroundColor Cyan
        Write-Host "  docker compose up -d" -ForegroundColor White
        Write-Host "  or" -ForegroundColor White
        Write-Host "  .\docker-start.ps1" -ForegroundColor White
    } else {
        throw "Docker not running"
    }
} catch {
    Write-Host "✗ Docker Desktop is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop from Start Menu" -ForegroundColor White
    Write-Host "2. Wait for Docker to fully start (icon in system tray should be green)" -ForegroundColor White
    Write-Host "3. Then run this script again or use: .\docker-start.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Trying to start Docker Desktop..." -ForegroundColor Cyan
    try {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
        Write-Host "✓ Docker Desktop launch command sent" -ForegroundColor Green
        Write-Host "Please wait 30-60 seconds for Docker to start, then try again" -ForegroundColor Yellow
    } catch {
        Write-Host "Could not auto-start Docker Desktop" -ForegroundColor Yellow
        Write-Host "Please start it manually from Start Menu" -ForegroundColor Yellow
    }
    exit 1
}

