@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 多账号钓鱼机器人 - 自动测试
echo ========================================
echo.

REM 步骤1：关闭所有现有的浏览器
echo [1/4] 关闭现有的浏览器进程...
taskkill /F /IM msedge.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ 已关闭现有浏览器
) else (
    echo ✓ 没有运行的浏览器
)
timeout /t 2 /nobreak >nul

REM 步骤2：启动两个浏览器
echo.
echo [2/4] 启动浏览器...
echo.

REM 查找 Edge 浏览器路径
set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_PATH%" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)
if not exist "%EDGE_PATH%" (
    echo ❌ 未找到 Edge 浏览器
    pause
    exit /b 1
)

echo 找到浏览器: %EDGE_PATH%
echo.

REM 启动账号1（端口 9222）
echo 启动账号1 (端口 9222)...
set PORT1=9222
set USERDATA1=%TEMP%\chrome-fishing-%PORT1%
start "" "%EDGE_PATH%" --remote-debugging-port=%PORT1% --user-data-dir="%USERDATA1%" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
echo ✓ 账号1浏览器已启动

timeout /t 3 /nobreak >nul

REM 启动账号2（端口 9223）
echo 启动账号2 (端口 9223)...
set PORT2=9223
set USERDATA2=%TEMP%\chrome-fishing-%PORT2%
start "" "%EDGE_PATH%" --remote-debugging-port=%PORT2% --user-data-dir="%USERDATA2%" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
echo ✓ 账号2浏览器已启动

echo.
echo ========================================
echo [3/4] 请在两个浏览器中登录账号
echo ========================================
echo.
echo 浏览器1（端口 9222）- 登录账号1
echo 浏览器2（端口 9223）- 登录账号2
echo.
echo 登录完成后，按任意键继续...
pause >nul

REM 步骤3：启动钓鱼脚本
echo.
echo [4/4] 启动钓鱼脚本...
echo.

REM 启动账号1的钓鱼脚本
echo 启动账号1钓鱼脚本...
start "Fishing Bot - Account1" cmd /k "python fishing0.5.py --port 9222 --name Account1 --auto-bind"
timeout /t 2 /nobreak >nul

REM 启动账号2的钓鱼脚本
echo 启动账号2钓鱼脚本...
start "Fishing Bot - Account2" cmd /k "python fishing0.5.py --port 9223 --name Account2 --auto-bind"

echo.
echo ========================================
echo ✓ 测试启动完成！
echo ========================================
echo.
echo 现在应该有：
echo   - 2个浏览器窗口（端口 9222 和 9223）
echo   - 2个钓鱼脚本窗口
echo.
echo 检查要点：
echo   1. 账号1窗口显示: CDP 端口: 127.0.0.1:9222
echo   2. 账号2窗口显示: CDP 端口: 127.0.0.1:9223
echo   3. 两个窗口的端口号应该不同
echo.
echo 按任意键退出启动器...
pause >nul
