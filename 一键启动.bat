@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo 多账号钓鱼机器人 - 一键启动
echo ========================================
echo.

REM 询问账号数量
set /p accountCount="请输入需要启动的账号数量 (1-5): "

REM 验证输入
if "%accountCount%"=="" (
    echo ❌ 请输入有效的数字
    pause
    exit /b 1
)

if %accountCount% LSS 1 (
    echo ❌ 账号数量必须大于 0
    pause
    exit /b 1
)

if %accountCount% GTR 5 (
    echo ❌ 账号数量不能超过 5
    pause
    exit /b 1
)

echo.
echo 准备启动 %accountCount% 个账号...
echo.

REM 步骤1：关闭现有浏览器
echo [1/4] 关闭现有的浏览器进程...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo ✓ 已清理现有浏览器
echo.

REM 步骤2：查找 Edge 浏览器
echo [2/4] 查找 Edge 浏览器...
set "EDGE_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_PATH%" (
    set "EDGE_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
)
if not exist "%EDGE_PATH%" (
    echo ❌ 未找到 Edge 浏览器
    echo 请确保已安装 Microsoft Edge
    pause
    exit /b 1
)

echo ✓ 找到浏览器: %EDGE_PATH%
echo.

REM 步骤3：启动浏览器
echo [3/4] 启动浏览器...
set BASE_PORT=9222

for /L %%i in (0,1,%accountCount%) do (
    if %%i LSS %accountCount% (
        set /a PORT=!BASE_PORT!+%%i
        set /a ACCOUNT_NUM=%%i+1
        set USERDATA=%TEMP%\chrome-fishing-!PORT!

        echo   启动 Account!ACCOUNT_NUM! ^(端口 !PORT!^)...
        start "" "%EDGE_PATH%" --remote-debugging-port=!PORT! --user-data-dir="!USERDATA!" --remote-allow-origins=* --disable-features=RendererCodeIntegrity
        timeout /t 2 /nobreak >nul
    )
)

echo ✓ 所有浏览器已启动
echo.

REM 等待用户登录
echo ========================================
echo 请在每个浏览器中登录账号
echo ========================================
echo.
echo 浏览器窗口数量: %accountCount%
echo 请在每个浏览器中：
echo   1. 访问游戏网站
echo   2. 登录对应的账号
echo   3. 进入钓鱼界面
echo.
pause

REM 步骤4：启动钓鱼脚本
echo.
echo [4/4] 启动钓鱼脚本...

if not exist "%~dp0fishing0.5.py" (
    echo ❌ 未找到 fishing0.5.py
    pause
    exit /b 1
)

for /L %%i in (0,1,%accountCount%) do (
    if %%i LSS %accountCount% (
        set /a PORT=!BASE_PORT!+%%i
        set /a ACCOUNT_NUM=%%i+1

        echo   启动 Account!ACCOUNT_NUM! 钓鱼脚本...
        start "Fishing Bot - Account!ACCOUNT_NUM!" cmd /k "python "%~dp0fishing0.5.py" --port !PORT! --name Account!ACCOUNT_NUM! --auto-bind"
        timeout /t 1 /nobreak >nul
    )
)

echo ✓ 所有钓鱼脚本已启动
echo.

REM 完成
echo ========================================
echo ✓ 启动完成！
echo ========================================
echo.
echo 现在应该有：
echo   - %accountCount% 个浏览器窗口
echo   - %accountCount% 个钓鱼脚本窗口
echo.
echo 检查要点：
for /L %%i in (0,1,%accountCount%) do (
    if %%i LSS %accountCount% (
        set /a PORT=!BASE_PORT!+%%i
        set /a ACCOUNT_NUM=%%i+1
        echo   Account!ACCOUNT_NUM! 窗口显示: CDP 端口: 127.0.0.1:!PORT!
    )
)
echo.
echo 操作说明：
echo   1. 在每个预览窗口中拖拽选择识别区域
echo   2. 按 F7 开始钓鱼
echo   3. 按 Esc 停止
echo.
pause
