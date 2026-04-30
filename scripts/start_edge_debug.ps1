# Start Edge with Remote Debugging Port
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Start Edge with Remote Debugging Port" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Edge..." -ForegroundColor Yellow
Write-Host "Debug Port: 9222"
Write-Host "Profile: $env:TEMP\edge-fishing"
Write-Host ""

# Try to find Edge
$edgePaths = @(
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

$edgePath = $null
foreach ($path in $edgePaths) {
    if (Test-Path $path) {
        $edgePath = $path
        break
    }
}

if ($null -eq $edgePath) {
    Write-Host "[ERROR] Edge browser not found" -ForegroundColor Red
    Write-Host "Please check if Edge is installed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Edge with debugging port
$arguments = @(
    "--remote-debugging-port=9222",
    "--remote-allow-origins=*",
    "--user-data-dir=$env:TEMP\edge-fishing"
)

Start-Process -FilePath $edgePath -ArgumentList $arguments

Write-Host "[OK] Edge started successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Instructions:" -ForegroundColor Cyan
Write-Host "1. Open game page in the Edge window"
Write-Host "2. Run fishing0.5.exe or python fishing0.5.py"
Write-Host "3. Press F8 to bind window, drag to select area, press F7 to start"
Write-Host ""
Read-Host "Press Enter to close this window"
