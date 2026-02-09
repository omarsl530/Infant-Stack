# run_python_simulation.ps1
# PowerShell script to run the Python API simulation
# This simulates IoT devices (infant tags, RTLS readers, gate terminals, etc.)
# and tests the backend APIs

param(
    [switch]$FastMode,
    [switch]$Debug,
    [string]$BackendUrl = "http://localhost:8000",
    [int]$NumInfants = 50,
    [int]$NumReaders = 10
)

$ErrorActionPreference = "Stop"

# Set environment variables
$env:BACKEND_URL = $BackendUrl
$env:NUM_INFANTS = $NumInfants
$env:NUM_READERS = $NumReaders

if ($FastMode) {
    $env:FAST_MODE = "1"
    Write-Host "Running in FAST MODE (reduced timers for testing)" -ForegroundColor Yellow
}

if ($Debug) {
    $env:DEBUG_MODE = "1"
    Write-Host "Running in DEBUG MODE (verbose logging)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Infant-Stack API Simulation" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend URL: $BackendUrl" -ForegroundColor White
Write-Host "Simulating $NumInfants infant tags and $NumReaders RTLS readers" -ForegroundColor White
Write-Host ""

# Check if aiohttp is installed
$pythonCmd = "python"
try {
    & $pythonCmd -c "import aiohttp" 2>$null
} catch {
    Write-Host "Installing required dependency: aiohttp..." -ForegroundColor Yellow
    & $pythonCmd -m pip install aiohttp
}

# Run the simulation
Write-Host "Starting simulation..." -ForegroundColor Green
Write-Host "(Press Ctrl+C to stop)" -ForegroundColor Gray
Write-Host ""

& $pythonCmd simulation_software/main.py
