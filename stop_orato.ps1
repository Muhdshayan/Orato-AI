Set-Location $PSScriptRoot

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "      Stopping Orato-AI Services         " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Stop Frontend
Write-Host "[1/3] Stopping React Frontend..." -ForegroundColor Yellow
if (Test-Path ".frontend.pid") {
    $pid = Get-Content ".frontend.pid"
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Remove-Item ".frontend.pid"
}
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*react-scripts*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Stop Backend & ASR Model Server
Write-Host "[2/3] Stopping FastAPI Backend and ASR Server..." -ForegroundColor Yellow
if (Test-Path ".backend.pid") {
    $pid = Get-Content ".backend.pid"
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    Remove-Item ".backend.pid"
}
Get-Process -Name "uvicorn" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*parakeet_model_server*" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 3. Stop Docker containers
Write-Host "[3/3] Stopping Docker containers..." -ForegroundColor Yellow
docker stop oratoaidb 2>$null | Out-Null
docker stop minio 2>$null | Out-Null

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "    All services stopped successfully!   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
