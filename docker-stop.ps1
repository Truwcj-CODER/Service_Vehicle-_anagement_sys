# PowerShell script to stop Docker Compose services
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Stopping Docker Compose Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Try docker compose (new syntax) first, then docker-compose (old syntax)
$composeCommand = $null
try {
    docker compose version > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        $composeCommand = "docker compose"
    }
} catch {
    try {
        docker-compose --version > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $composeCommand = "docker-compose"
        }
    } catch {
        Write-Host "✗ Docker Compose not found" -ForegroundColor Red
        exit 1
    }
}

# Stop services
& $composeCommand.Split(' ') down

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Services stopped successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗ Failed to stop services" -ForegroundColor Red
    exit 1
}


