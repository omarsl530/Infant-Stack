# run_simulations.ps1
# PowerShell script to run Wokwi simulations on Windows
# Requires: Wokwi CLI installed and WOKWI_CLI_TOKEN set

param(
    [int]$TimeoutMinutes = 60
)

$ErrorActionPreference = "Stop"

# Load .env if it exists
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^([^#][^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# Check for WOKWI_CLI_TOKEN
if (-not $env:WOKWI_CLI_TOKEN) {
    Write-Host "Error: WOKWI_CLI_TOKEN is not set." -ForegroundColor Red
    Write-Host "Please get a free token from https://wokwi.com/dashboard/ci"
    Write-Host "Then run: `$env:WOKWI_CLI_TOKEN = 'your_token_here'"
    exit 1
}

# Find Wokwi CLI
$wokwiCli = Get-Command "wokwi-cli" -ErrorAction SilentlyContinue
if (-not $wokwiCli) {
    # Try common install locations
    $possiblePaths = @(
        "$env:USERPROFILE\.wokwi\bin\wokwi-cli.exe",
        "$env:LOCALAPPDATA\Programs\wokwi-cli\wokwi-cli.exe",
        "C:\Program Files\wokwi-cli\wokwi-cli.exe"
    )
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $wokwiCli = $path
            break
        }
    }
}

if (-not $wokwiCli) {
    Write-Host "Error: wokwi-cli not found. Please install it from https://docs.wokwi.com/wokwi-ci/getting-started" -ForegroundColor Red
    exit 1
}

Write-Host "Starting Simulations in Background ($TimeoutMinutes minute timeout)..." -ForegroundColor Cyan

# Cleanup old processes
$pidFile = ".wokwi_pids.txt"
if (Test-Path $pidFile) {
    Write-Host "Cleaning up old processes..."
    Get-Content $pidFile | ForEach-Object {
        $pid = $_
        try {
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        } catch {}
    }
    Remove-Item $pidFile
}

$timeoutMs = $TimeoutMinutes * 60 * 1000
$pids = @()

# Function to start a simulation
function Start-Simulation {
    param([string]$Dir)
    
    Write-Host "Starting $Dir..." -ForegroundColor Yellow
    
    $process = Start-Process -FilePath $wokwiCli -ArgumentList "$Dir --timeout $timeoutMs" -PassThru -WindowStyle Hidden
    
    Write-Host "$Dir started (PID $($process.Id))" -ForegroundColor Green
    return $process.Id
}

# Start all simulations
$simDirs = @(
    "simulations/wokwi/infant_tag",
    "simulations/wokwi/mother_tag",
    "simulations/wokwi/gate_reader",
    "simulations/wokwi/gate_terminal",
    "simulations/wokwi/esp32-micropython-ssd1306"
)

foreach ($dir in $simDirs) {
    if (Test-Path $dir) {
        $pid = Start-Simulation -Dir $dir
        $pids += $pid
    } else {
        Write-Host "Warning: $dir not found, skipping" -ForegroundColor Yellow
    }
}

# Save PIDs
$pids | Out-File $pidFile

Write-Host ""
Write-Host "All simulations started! You have $TimeoutMinutes minutes." -ForegroundColor Cyan
Write-Host "Wait 5 seconds for them to boot..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Simulations are running. To stop them manually, run:" -ForegroundColor Green
Write-Host "  Get-Content .wokwi_pids.txt | ForEach-Object { Stop-Process -Id `$_ -Force }" -ForegroundColor White
Write-Host "  Remove-Item .wokwi_pids.txt" -ForegroundColor White
