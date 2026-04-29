# Multi-Account Fishing Bot - Complete Startup Script
# This script automates the entire startup process

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Multi-Account Fishing Bot" -ForegroundColor Cyan
Write-Host "Complete Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Ask for account count
$accountCount = Read-Host "How many accounts do you want to start (1-5)?"
$accountCount = [int]$accountCount

if ($accountCount -lt 1 -or $accountCount -gt 5) {
    Write-Host "ERROR: Account count must be between 1 and 5" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Preparing to start $accountCount account(s)..." -ForegroundColor Green
Write-Host ""

# Step 1: Close existing browsers
Write-Host "[1/4] Closing existing browsers..." -ForegroundColor Yellow
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Write-Host "Done." -ForegroundColor Green
Write-Host ""

# Step 2: Find Edge browser
Write-Host "[2/4] Finding Edge browser..." -ForegroundColor Yellow
$edgePaths = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
)

$edgePath = $null
foreach ($path in $edgePaths) {
    if (Test-Path $path) {
        $edgePath = $path
        break
    }
}

if ($null -eq $edgePath) {
    Write-Host "ERROR: Microsoft Edge not found" -ForegroundColor Red
    Write-Host "Please make sure Microsoft Edge is installed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Found: $edgePath" -ForegroundColor Green
Write-Host ""

# Step 3 & 4: Start browsers and fishing scripts one by one
Write-Host "[3/4] Starting accounts one by one..." -ForegroundColor Yellow
Write-Host "This avoids port conflicts by starting each account sequentially." -ForegroundColor Gray
Write-Host ""

$basePort = 9222
$scriptPath = Join-Path $PSScriptRoot "fishing0.5.py"

if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: fishing0.5.py not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Hotkey mapping
$hotkeyMap = @{
    0 = "F7"
    1 = "F9"
    2 = "F10"
    3 = "F11"
    4 = "F12"
}

for ($i = 0; $i -lt $accountCount; $i++) {
    $port = $basePort + $i
    $accountName = "Account$($i + 1)"
    $hotkey = $hotkeyMap[$i]
    $userDataDir = "$env:TEMP\chrome-fishing-$port"

    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Setting up $accountName (Port: $port, Hotkey: $hotkey)" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Start browser
    Write-Host "[Step 1/3] Starting browser..." -ForegroundColor Yellow
    $arguments = @(
        "--remote-debugging-port=$port",
        "--user-data-dir=`"$userDataDir`"",
        "--remote-allow-origins=*",
        "--disable-features=RendererCodeIntegrity"
    )
    Start-Process -FilePath $edgePath -ArgumentList $arguments
    Start-Sleep -Seconds 3
    Write-Host "Browser started." -ForegroundColor Green
    Write-Host ""

    # Wait for login
    Write-Host "[Step 2/3] Please login to $accountName" -ForegroundColor Yellow
    Write-Host "  1. Visit the game website" -ForegroundColor White
    Write-Host "  2. Login to your account" -ForegroundColor White
    Write-Host "  3. Go to fishing page" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter when logged in and ready"

    # Start fishing script
    Write-Host ""
    Write-Host "[Step 3/3] Starting fishing script..." -ForegroundColor Yellow
    $cmd = "python `"$scriptPath`" --port $port --name $accountName --auto-bind"
    Start-Process cmd -ArgumentList "/k", $cmd -WindowStyle Normal
    Start-Sleep -Seconds 2
    Write-Host "Fishing script started." -ForegroundColor Green
    Write-Host ""

    Write-Host "Next steps for $accountName" -ForegroundColor Yellow
    Write-Host "  1. In the fishing script window, select the browser window (enter window number)" -ForegroundColor White
    Write-Host "  2. Drag to select fishing area in the preview window" -ForegroundColor White
    Write-Host "  3. Press $hotkey to start fishing" -ForegroundColor Cyan
    Write-Host ""

    if ($i -lt $accountCount - 1) {
        Read-Host "Press Enter to continue to next account"
        Write-Host ""
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "All accounts setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Complete
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Startup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You should now have:" -ForegroundColor Yellow
Write-Host "  - $accountCount browser window(s)" -ForegroundColor White
Write-Host "  - $accountCount fishing script window(s)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. In each fishing script window, select the browser window (enter 0, 1, 2...)" -ForegroundColor White
Write-Host "  2. Drag to select fishing area in each preview window" -ForegroundColor White
Write-Host "  3. Press the assigned hotkey to start fishing:" -ForegroundColor White
for ($i = 0; $i -lt $accountCount; $i++) {
    $accountName = "Account$($i + 1)"
    $hotkey = $hotkeyMap[$i]
    Write-Host "     - $accountName : $hotkey" -ForegroundColor Cyan
}
Write-Host "  4. Press Esc to stop" -ForegroundColor White
Write-Host ""
Write-Host "Important: Each account has a different hotkey to avoid conflicts!" -ForegroundColor Yellow
Write-Host ""
Read-Host "Press Enter to exit this launcher"
