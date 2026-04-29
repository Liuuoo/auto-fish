# 多账号钓鱼机器人 - 一键启动脚本
# 使用方法：右键点击，选择"使用 PowerShell 运行"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "多账号钓鱼机器人 - 一键启动" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 询问账号数量
$accountCount = Read-Host "请输入需要启动的账号数量 (1-5)"
$accountCount = [int]$accountCount

if ($accountCount -lt 1 -or $accountCount -gt 5) {
    Write-Host "❌ 账号数量必须在 1-5 之间" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host ""
Write-Host "准备启动 $accountCount 个账号..." -ForegroundColor Green
Write-Host ""

# 步骤1：关闭现有浏览器
Write-Host "[1/4] 关闭现有的浏览器进程..." -ForegroundColor Yellow
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Write-Host "✓ 已清理现有浏览器" -ForegroundColor Green
Write-Host ""

# 步骤2：查找 Edge 浏览器
Write-Host "[2/4] 查找 Edge 浏览器..." -ForegroundColor Yellow
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
    Write-Host "❌ 未找到 Microsoft Edge 浏览器" -ForegroundColor Red
    Write-Host "请确保已安装 Microsoft Edge" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

Write-Host "✓ 找到浏览器: $edgePath" -ForegroundColor Green
Write-Host ""

# 步骤3：启动浏览器
Write-Host "[3/4] 启动浏览器..." -ForegroundColor Yellow
$basePort = 9222

for ($i = 0; $i -lt $accountCount; $i++) {
    $port = $basePort + $i
    $accountName = "Account$($i + 1)"
    $userDataDir = "$env:TEMP\chrome-fishing-$port"

    Write-Host "  启动 $accountName (端口 $port)..." -ForegroundColor Cyan

    $arguments = @(
        "--remote-debugging-port=$port",
        "--user-data-dir=`"$userDataDir`"",
        "--remote-allow-origins=*",
        "--disable-features=RendererCodeIntegrity"
    )

    Start-Process -FilePath $edgePath -ArgumentList $arguments
    Start-Sleep -Seconds 2
}

Write-Host "✓ 所有浏览器已启动" -ForegroundColor Green
Write-Host ""

# 等待用户登录
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "请在每个浏览器中登录账号" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "浏览器窗口数量: $accountCount" -ForegroundColor Yellow
Write-Host "请在每个浏览器中：" -ForegroundColor Yellow
Write-Host "  1. 访问游戏网站" -ForegroundColor White
Write-Host "  2. 登录对应的账号" -ForegroundColor White
Write-Host "  3. 进入钓鱼界面" -ForegroundColor White
Write-Host ""
Read-Host "完成后按 Enter 继续"

# 步骤4：启动钓鱼脚本
Write-Host ""
Write-Host "[4/4] 启动钓鱼脚本..." -ForegroundColor Yellow

$scriptPath = Join-Path $PSScriptRoot "fishing0.5.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "❌ 未找到 fishing0.5.py" -ForegroundColor Red
    Read-Host "按 Enter 退出"
    exit 1
}

for ($i = 0; $i -lt $accountCount; $i++) {
    $port = $basePort + $i
    $accountName = "Account$($i + 1)"

    Write-Host "  启动 $accountName 钓鱼脚本..." -ForegroundColor Cyan

    $cmd = "python `"$scriptPath`" --port $port --name $accountName --auto-bind"

    # 在新的命令行窗口中启动
    Start-Process cmd -ArgumentList "/k", $cmd -WindowStyle Normal

    Start-Sleep -Seconds 1
}

Write-Host "✓ 所有钓鱼脚本已启动" -ForegroundColor Green
Write-Host ""

# 完成
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ 启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "现在应该有：" -ForegroundColor Yellow
Write-Host "  - $accountCount 个浏览器窗口" -ForegroundColor White
Write-Host "  - $accountCount 个钓鱼脚本窗口" -ForegroundColor White
Write-Host ""
Write-Host "检查要点：" -ForegroundColor Yellow
for ($i = 0; $i -lt $accountCount; $i++) {
    $port = $basePort + $i
    $accountName = "Account$($i + 1)"
    Write-Host "  $accountName 窗口显示: CDP 端口: 127.0.0.1:$port" -ForegroundColor White
}
Write-Host ""
Write-Host "操作说明：" -ForegroundColor Yellow
Write-Host "  1. 在每个预览窗口中拖拽选择识别区域" -ForegroundColor White
Write-Host "  2. 按 F7 开始钓鱼" -ForegroundColor White
Write-Host "  3. 按 Esc 停止" -ForegroundColor White
Write-Host ""
Read-Host "按 Enter 退出启动器"
