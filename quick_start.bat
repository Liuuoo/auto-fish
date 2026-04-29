@echo off
REM Multi-Account Fishing Bot - Quick Start
REM Double-click to run

echo ========================================
echo Multi-Account Fishing Bot - Quick Start
echo ========================================
echo.

REM Ask for account count
set /p accountCount="How many accounts do you want to start (1-5)? "

REM Validate input
if "%accountCount%"=="" (
    echo ERROR: Please enter a valid number
    pause
    exit /b 1
)

if %accountCount% LSS 1 (
    echo ERROR: Account count must be greater than 0
    pause
    exit /b 1
)

if %accountCount% GTR 5 (
    echo ERROR: Account count cannot exceed 5
    pause
    exit /b 1
)

echo.
echo Preparing to start %accountCount% account(s)...
echo.

REM Step 1: Close existing browsers
echo [1/4] Closing existing browsers...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo Done.
echo.

REM Step 2: Find Edge browser
echo [2/4] Finding Edge browser...
set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_PATH%" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)
if not exist "%EDGE_PATH%" (
    echo ERROR: Microsoft Edge not found
    echo Please make sure Microsoft Edge is installed
    pause
    exit /b 1
)

echo Found: %EDGE_PATH%
echo.

REM Step 3: Start browsers
echo [3/4] Starting browsers...
set BASE_PORT=9222

REM Start Account 1
if %accountCount% GEQ 1 (
    set /a PORT1=%BASE_PORT%+0
    set USERDATA1=%TEMP%\chrome-fishing-!PORT1!
    echo   Starting Account1 ^(port !PORT1!^)...
    start "" "%EDGE_PATH%" --remote-debugging-port=!PORT1! --user-data-dir="!USERDATA1!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
    timeout /t 2 /nobreak >nul
)

REM Start Account 2
if %accountCount% GEQ 2 (
    set /a PORT2=%BASE_PORT%+1
    set USERDATA2=%TEMP%\chrome-fishing-!PORT2!
    echo   Starting Account2 ^(port !PORT2!^)...
    start "" "%EDGE_PATH%" --remote-debugging-port=!PORT2! --user-data-dir="!USERDATA2!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
    timeout /t 2 /nobreak >nul
)

REM Start Account 3
if %accountCount% GEQ 3 (
    set /a PORT3=%BASE_PORT%+2
    set USERDATA3=%TEMP%\chrome-fishing-!PORT3!
    echo   Starting Account3 ^(port !PORT3!^)...
    start "" "%EDGE_PATH%" --remote-debugging-port=!PORT3! --user-data-dir="!USERDATA3!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
    timeout /t 2 /nobreak >nul
)

REM Start Account 4
if %accountCount% GEQ 4 (
    set /a PORT4=%BASE_PORT%+3
    set USERDATA4=%TEMP%\chrome-fishing-!PORT4!
    echo   Starting Account4 ^(port !PORT4!^)...
    start "" "%EDGE_PATH%" --remote-debugging-port=!PORT4! --user-data-dir="!USERDATA4!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
    timeout /t 2 /nobreak >nul
)

REM Start Account 5
if %accountCount% GEQ 5 (
    set /a PORT5=%BASE_PORT%+4
    set USERDATA5=%TEMP%\chrome-fishing-!PORT5!
    echo   Starting Account5 ^(port !PORT5!^)...
    start "" "%EDGE_PATH%" --remote-debugging-port=!PORT5! --user-data-dir="!USERDATA5!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
    timeout /t 2 /nobreak >nul
)

echo Done. All browsers started.
echo.

REM Wait for user to login
echo ========================================
echo Please login to your accounts
echo ========================================
echo.
echo Browser windows: %accountCount%
echo Please in each browser:
echo   1. Visit the game website
echo   2. Login to your account
echo   3. Go to fishing page
echo.
pause

REM Step 4: Start fishing scripts
echo.
echo [4/4] Starting fishing scripts...

if not exist "%~dp0fishing0.5.py" (
    echo ERROR: fishing0.5.py not found
    pause
    exit /b 1
)

REM Start Account 1 script
if %accountCount% GEQ 1 (
    set /a PORT1=%BASE_PORT%+0
    echo   Starting Account1 fishing script...
    start "Fishing Bot - Account1" cmd /k "python "%~dp0fishing0.5.py" --port !PORT1! --name Account1 --auto-bind"
    timeout /t 1 /nobreak >nul
)

REM Start Account 2 script
if %accountCount% GEQ 2 (
    set /a PORT2=%BASE_PORT%+1
    echo   Starting Account2 fishing script...
    start "Fishing Bot - Account2" cmd /k "python "%~dp0fishing0.5.py" --port !PORT2! --name Account2 --auto-bind"
    timeout /t 1 /nobreak >nul
)

REM Start Account 3 script
if %accountCount% GEQ 3 (
    set /a PORT3=%BASE_PORT%+2
    echo   Starting Account3 fishing script...
    start "Fishing Bot - Account3" cmd /k "python "%~dp0fishing0.5.py" --port !PORT3! --name Account3 --auto-bind"
    timeout /t 1 /nobreak >nul
)

REM Start Account 4 script
if %accountCount% GEQ 4 (
    set /a PORT4=%BASE_PORT%+3
    echo   Starting Account4 fishing script...
    start "Fishing Bot - Account4" cmd /k "python "%~dp0fishing0.5.py" --port !PORT4! --name Account4 --auto-bind"
    timeout /t 1 /nobreak >nul
)

REM Start Account 5 script
if %accountCount% GEQ 5 (
    set /a PORT5=%BASE_PORT%+4
    echo   Starting Account5 fishing script...
    start "Fishing Bot - Account5" cmd /k "python "%~dp0fishing0.5.py" --port !PORT5! --name Account5 --auto-bind"
    timeout /t 1 /nobreak >nul
)

echo Done. All fishing scripts started.
echo.

REM Complete
echo ========================================
echo Startup Complete!
echo ========================================
echo.
echo You should now have:
echo   - %accountCount% browser window(s)
echo   - %accountCount% fishing script window(s)
echo.
echo Check points:
echo   Account1 window shows: CDP port: 127.0.0.1:9222
if %accountCount% GEQ 2 echo   Account2 window shows: CDP port: 127.0.0.1:9223
if %accountCount% GEQ 3 echo   Account3 window shows: CDP port: 127.0.0.1:9224
if %accountCount% GEQ 4 echo   Account4 window shows: CDP port: 127.0.0.1:9225
if %accountCount% GEQ 5 echo   Account5 window shows: CDP port: 127.0.0.1:9226
echo.
echo Instructions:
echo   1. Drag to select fishing area in each preview window
echo   2. Press F7 to start fishing
echo   3. Press Esc to stop
echo.
pause
