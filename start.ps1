# Fishing Bot - One-Click Startup Script
# This script automates the entire startup process

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fishing Bot - One-Click Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Close existing browsers
Write-Host "[1/4] Closing existing browsers..." -ForegroundColor Yellow
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "Done." -ForegroundColor Green
Write-Host ""

# Step 2: Find browser (Edge or Chrome)
Write-Host "[2/4] Finding browser..." -ForegroundColor Yellow
$browserPath = $null
$browserName = ""

# Try Edge first
$edgePaths = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)

foreach ($path in $edgePaths) {
    if (Test-Path $path) {
        $browserPath = $path
        $browserName = "Microsoft Edge"
        break
    }
}

# Try Chrome if Edge not found
if ($null -eq $browserPath) {
    $chromePaths = @(
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
    )

    foreach ($path in $chromePaths) {
        if (Test-Path $path) {
            $browserPath = $path
            $browserName = "Google Chrome"
            break
        }
    }
}

if ($null -eq $browserPath) {
    Write-Host "ERROR: Browser not found" -ForegroundColor Red
    Write-Host "Please make sure Microsoft Edge or Google Chrome is installed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found: $browserName" -ForegroundColor Green
Write-Host "Path: $browserPath" -ForegroundColor Gray
Write-Host ""

# Step 3: Start browser with debugging port
Write-Host "[3/4] Starting browser with debugging port..." -ForegroundColor Yellow
$port = 9222
$userDataDir = "$env:TEMP\chrome-fishing"

$arguments = @(
    "--remote-debugging-port=$port",
    "--user-data-dir=`"$userDataDir`"",
    "--remote-allow-origins=*",
    "--disable-features=RendererCodeIntegrity"
)

Start-Process -FilePath $browserPath -ArgumentList $arguments
Start-Sleep -Seconds 3
Write-Host "Browser started on port $port" -ForegroundColor Green
Write-Host ""

# Wait for user to login
Write-Host "Please complete the following steps:" -ForegroundColor Yellow
Write-Host "  1. Visit the game website" -ForegroundColor White
Write-Host "  2. Login to your account" -ForegroundColor White
Write-Host "  3. Navigate to the fishing page" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter when you're ready to start fishing"

# Step 4: Start fishing script
Write-Host ""
Write-Host "[4/4] Starting fishing script..." -ForegroundColor Yellow

$scriptPath = Join-Path $PSScriptRoot "fishing0.5.py"

if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: fishing0.5.py not found at $scriptPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$cmd = "python `"$scriptPath`""
Start-Process cmd -ArgumentList "/k", $cmd -WindowStyle Normal
Start-Sleep -Seconds 2
Write-Host "Fishing script started." -ForegroundColor Green
Write-Host ""

# Complete
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Startup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. In the fishing script window:" -ForegroundColor White
Write-Host "     - Press F8 to bind the browser window" -ForegroundColor Cyan
Write-Host "     - Drag to select the fishing area in the preview window" -ForegroundColor White
Write-Host "  2. Press F7 to start fishing" -ForegroundColor Cyan
Write-Host "  3. Press F1 for equipment crafting" -ForegroundColor Cyan
Write-Host "  4. Press ESC to stop" -ForegroundColor White
Write-Host ""
Write-Host "Hotkeys:" -ForegroundColor Yellow
Write-Host "  F8  - Bind browser window" -ForegroundColor Cyan
Write-Host "  F7  - Start/Pause fishing" -ForegroundColor Cyan
Write-Host "  F1  - Equipment crafting" -ForegroundColor Cyan
Write-Host "  ESC - Stop/Exit" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit this launcher"
