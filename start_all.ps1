# PowerShell Startup Script for Windows Docker Container
# Starts both FastAPI backend and .NET Core frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Fraud Detection System" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Set error action preference
$ErrorActionPreference = "Continue"

# Verify Python installation
Write-Host "`n[1/5] Verifying Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "[OK] Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found!" -ForegroundColor Red
    exit 1
}

# Verify critical files
Write-Host "`n[2/5] Verifying application files..." -ForegroundColor Yellow
$criticalFiles = @(
    "C:\app\api\api.py",
    "C:\app\backend\hybrid_decision.py",
    "C:\app\backend\model\isolation_forest.pkl",
    "C:\app\backend\model\autoencoder.h5",
    "C:\app\ConfigManagementUI.dll"
)

$allFilesExist = $true
foreach ($file in $criticalFiles) {
    if (Test-Path $file) {
        Write-Host "[OK] Found: $file" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Missing: $file" -ForegroundColor Red
        $allFilesExist = $false
    }
}

if (-not $allFilesExist) {
    Write-Host "`nCritical files missing! Exiting..." -ForegroundColor Red
    exit 1
}

# Set environment variables
Write-Host "`n[3/5] Setting environment variables..." -ForegroundColor Yellow
$env:PYTHONPATH = "C:\app;C:\app\api;C:\app\backend"
$env:PYTHONUNBUFFERED = "1"
Write-Host "[OK] PYTHONPATH: $env:PYTHONPATH" -ForegroundColor Green

# Start FastAPI Backend
Write-Host "`n[4/5] Starting FastAPI Backend (Port 8000)..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    Set-Location C:\app
    $env:PYTHONPATH = "C:\app;C:\app\api;C:\app\backend"
    python -m uvicorn api.api:app --host 0.0.0.0 --port 8000 --workers 1
}

Write-Host "[OK] FastAPI started (Job ID: $($apiJob.Id))" -ForegroundColor Green

# Wait for API to be ready
Write-Host "  Waiting for API to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Test API health
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 10 -UseBasicParsing
    Write-Host "[OK] API Health Check: OK" -ForegroundColor Green
} catch {
    Write-Host "[WARN] API Health Check: Failed (will retry later)" -ForegroundColor Yellow
}

# Start .NET Frontend
Write-Host "`n[5/5] Starting .NET Configuration UI (Port 5202)..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location C:\app
    dotnet ConfigManagementUI.dll --urls "http://0.0.0.0:5202"
}

Write-Host "[OK] .NET UI started (Job ID: $($frontendJob.Id))" -ForegroundColor Green

# Display startup summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] System Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor White
Write-Host "API Health Check: http://localhost:8000/api/health" -ForegroundColor White
Write-Host "Configuration UI: http://localhost:5202" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan

# Monitor both jobs
Write-Host "`nMonitoring services (Press Ctrl+C to stop)..." -ForegroundColor Yellow

try {
    while ($true) {
        # Check API job status
        $apiState = (Get-Job -Id $apiJob.Id).State
        $frontendState = (Get-Job -Id $frontendJob.Id).State
        
        if ($apiState -eq "Failed") {
            Write-Host "`n[ERROR] API Job Failed!" -ForegroundColor Red
            Receive-Job -Id $apiJob.Id
            break
        }
        
        if ($frontendState -eq "Failed") {
            Write-Host "`n[ERROR] Frontend Job Failed!" -ForegroundColor Red
            Receive-Job -Id $frontendJob.Id
            break
        }
        
        # Display job output
        Receive-Job -Id $apiJob.Id
        Receive-Job -Id $frontendJob.Id
        
        Start-Sleep -Seconds 2
    }
} finally {
    # Cleanup on exit
    Write-Host "`n`nShutting down services..." -ForegroundColor Yellow
    Stop-Job -Id $apiJob.Id -ErrorAction SilentlyContinue
    Stop-Job -Id $frontendJob.Id -ErrorAction SilentlyContinue
    Remove-Job -Id $apiJob.Id -Force -ErrorAction SilentlyContinue
    Remove-Job -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Services stopped" -ForegroundColor Green
}
