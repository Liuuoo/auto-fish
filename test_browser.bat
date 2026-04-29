@echo off
REM Simple test script to diagnose browser startup issues

echo ========================================
echo Browser Startup Test
echo ========================================
echo.

REM Find Edge browser
echo Step 1: Finding Edge browser...
set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_PATH%" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)

if not exist "%EDGE_PATH%" (
    echo ERROR: Edge browser not found at:
    echo   C:\Program Files\Microsoft\Edge\Application\msedge.exe
    echo   C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe
    echo.
    echo Please check if Edge is installed.
    pause
    exit /b 1
)

echo Found: %EDGE_PATH%
echo.

REM Test browser startup
echo Step 2: Testing browser startup...
echo Command: "%EDGE_PATH%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-fishing-9222" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
echo.
echo Starting browser...

start "" "%EDGE_PATH%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-fishing-9222" --remote-allow-origins=* --disable-features=RendererCodeIntegrity

echo.
echo If browser window opened, the test is successful!
echo If not, there might be a permission or configuration issue.
echo.
pause
