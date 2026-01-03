# PowerShell script to start Docker Compose services
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Docker Compose Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not found"
    }
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Docker Desktop from:" -ForegroundColor Yellow
    Write-Host "https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "See DOCKER_INSTALL_GUIDE.md for detailed instructions" -ForegroundColor Yellow
    exit 1
}

# Check if Docker is running
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker not running"
    }
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Desktop is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop from Start Menu" -ForegroundColor White
    Write-Host "2. Wait for Docker to fully start (icon in system tray should be green)" -ForegroundColor White
    Write-Host "3. Then run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Trying to start Docker Desktop..." -ForegroundColor Cyan
    try {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -ErrorAction SilentlyContinue
        Write-Host "✓ Docker Desktop launch command sent" -ForegroundColor Green
        Write-Host "Please wait 30-60 seconds for Docker to start, then run this script again" -ForegroundColor Yellow
    } catch {
        Write-Host "Could not auto-start Docker Desktop" -ForegroundColor Yellow
        Write-Host "Please start it manually from Start Menu" -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""

# Try docker compose (new syntax) first, then docker-compose (old syntax)
$composeCommand = $null
try {
    docker compose version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $composeCommand = "docker compose"
        Write-Host "✓ Using 'docker compose' (new syntax)" -ForegroundColor Green
    }
} catch {
    # Try old syntax
    try {
        docker-compose --version > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $composeCommand = "docker-compose"
            Write-Host "✓ Using 'docker-compose' (old syntax)" -ForegroundColor Green
        }
    } catch {
        Write-Host "✗ Docker Compose not found" -ForegroundColor Red
        Write-Host "Please ensure Docker Desktop is fully installed" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Cyan
Write-Host ""

# Start services
& $composeCommand.Split(' ') up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Waiting for services to initialize..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Application is running at:" -ForegroundColor Green
    Write-Host "- Web: http://localhost:5000" -ForegroundColor White
    Write-Host "- Login: http://localhost:5000/login" -ForegroundColor White
    Write-Host "- API Docs: http://localhost:5000/docs" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  View logs: $composeCommand logs -f" -ForegroundColor White
    Write-Host "  Stop: $composeCommand down" -ForegroundColor White
    Write-Host "  Status: $composeCommand ps" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    Write-Host "Check logs with: $composeCommand logs" -ForegroundColor Yellow
    exit 1
}


