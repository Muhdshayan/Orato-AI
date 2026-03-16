# Ensure we are in the project root
Set-Location $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "      Starting Orato-AI Services         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Start Docker containers
Write-Host "[1/3] Starting Docker containers (PostgreSQL, MinIO)..." -ForegroundColor Yellow

docker start oratoaidb 2>$null
if ($LASTEXITCODE -ne 0) {
    docker run --name oratoaidb -e POSTGRES_PASSWORD=orato123 -p 5432:5432 -d postgres | Out-Null
}

docker start minio 2>$null
if ($LASTEXITCODE -ne 0) {
    docker run -p 9000:9000 -p 9001:9001 `
        -e MINIO_ROOT_USER=MINIO_ACCESS `
        -e MINIO_ROOT_PASSWORD=MINIO_SECRET `
        -v "${PSScriptRoot}/minio-data:/data" `
        --name minio -d minio/minio server /data --console-address ":9001" | Out-Null
}

# 2. Start Backend
Write-Host "[2/3] Starting FastAPI Backend..." -ForegroundColor Yellow

$env:PYTHONPATH = "$PSScriptRoot"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$backendProcess = Start-Process -FilePath "$PSScriptRoot\venv\Scripts\uvicorn.exe" `
    -ArgumentList "main:app", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory "$PSScriptRoot\backend" `
    -RedirectStandardOutput "$PSScriptRoot\backend\backend.log" `
    -RedirectStandardError "$PSScriptRoot\backend\backend_err.log" `
    -PassThru -NoNewWindow
$backendProcess.Id | Out-File "$PSScriptRoot\.backend.pid"
Write-Host "   Backend PID: $($backendProcess.Id)" -ForegroundColor Green

# 3. Start Frontend
Write-Host "[3/3] Starting React Frontend..." -ForegroundColor Yellow

$env:BROWSER = "none"
$frontendProcess = Start-Process -FilePath "cmd.exe" `
    -ArgumentList "/c", "npm run start > `"$PSScriptRoot\frontend\frontend.log`" 2> `"$PSScriptRoot\frontend\frontend_err.log`"" `
    -WorkingDirectory "$PSScriptRoot\frontend" `
    -PassThru -NoNewWindow
$frontendProcess.Id | Out-File "$PSScriptRoot\.frontend.pid"
Write-Host "   Frontend PID: $($frontendProcess.Id)" -ForegroundColor Green

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "        Orato-AI is now running!         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Frontend Dashboard : http://localhost:3000" -ForegroundColor White
Write-Host "  Backend API Docs   : http://localhost:8000/docs" -ForegroundColor White
Write-Host "  MinIO Console      : http://localhost:9001" -ForegroundColor White
Write-Host ""
Write-Host "Logs: backend\backend.log and frontend\frontend.log" -ForegroundColor Gray
Write-Host "Press Ctrl+C to stop all services, or run .\stop_orato.ps1 in another terminal." -ForegroundColor Gray

# Graceful shutdown on Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 2
        # Check if processes are still running
        if ($backendProcess.HasExited) {
            Write-Host "Backend process stopped unexpectedly. Check backend\backend_err.log" -ForegroundColor Red
        }
        if ($frontendProcess.HasExited) {
            Write-Host "Frontend process stopped unexpectedly. Check frontend\frontend_err.log" -ForegroundColor Red
        }
    }
} finally {
    Write-Host "`nShutting down all services..." -ForegroundColor Yellow
    if (Test-Path "$PSScriptRoot\stop_orato.ps1") {
        & "$PSScriptRoot\stop_orato.ps1"
    } else {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
        Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue
        Write-Host "Services stopped." -ForegroundColor Green
    }
}
