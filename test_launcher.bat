@echo off
chcp 65001 >nul
echo ========================================
echo 测试多账号启动器
echo ========================================
echo.

REM 关闭所有现有的 Edge 进程
echo [1/3] 关闭现有的浏览器进程...
taskkill /F /IM msedge.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM 启动启动器
echo.
echo [2/3] 启动多账号启动器...
echo.
python launcher.py

echo.
echo [3/3] 测试完成
pause
