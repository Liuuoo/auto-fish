# 多账号钓鱼机器人 - 手动启动指南

由于批处理脚本在你的系统上无法正常运行，请按照以下步骤手动启动：

## 步骤1：打开 PowerShell

按 `Win + X`，选择"Windows PowerShell"或"终端"

## 步骤2：关闭现有浏览器

```powershell
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force
```

## 步骤3：启动浏览器

**一次性复制以下所有命令，粘贴到 PowerShell 中：**

```powershell
# 关闭现有浏览器
Get-Process msedge -ErrorAction SilentlyContinue | Stop-Process -Force

# 等待2秒
Start-Sleep -Seconds 2

# 设置正确的 Edge 路径（根据你的系统调整）
$edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 启动账号1（端口 9222）
Write-Host "Starting Account1 (port 9222)..." -ForegroundColor Green
Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=9222","--user-data-dir=`"$env:TEMP\chrome-fishing-9222`"","--remote-allow-origins=*","--disable-features=RendererCodeIntegrity"

# 等待2秒
Start-Sleep -Seconds 2

# 启动账号2（端口 9223）
Write-Host "Starting Account2 (port 9223)..." -ForegroundColor Green
Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=9223","--user-data-dir=`"$env:TEMP\chrome-fishing-9223`"","--remote-allow-origins=*","--disable-features=RendererCodeIntegrity"

Write-Host ""
Write-Host "Browsers started! Please login to your accounts." -ForegroundColor Cyan
```

**注意：** 如果上述命令提示找不到文件，请尝试以下路径之一：
- `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（32位版本）
- `C:\Program Files\Microsoft\Edge\Application\msedge.exe`（64位版本）

## 步骤4：在浏览器中登录账号

在两个浏览器窗口中分别登录账号，进入钓鱼界面

## 步骤5：启动钓鱼脚本

### 打开第一个命令行窗口

按 `Win + R`，输入 `cmd`，回车

然后运行：
```bash
cd "E:\UsersData\Desktop\Project\fish\origin"
python fishing0.5.py --port 9222 --name Account1 --auto-bind
```

### 打开第二个命令行窗口

再次按 `Win + R`，输入 `cmd`，回车

然后运行：
```bash
cd "E:\UsersData\Desktop\Project\fish\origin"
python fishing0.5.py --port 9223 --name Account2 --auto-bind
```

## 步骤6：开始钓鱼

在每个预览窗口中：
1. 拖拽选择识别区域
2. 按 `F7` 开始钓鱼
3. 按 `Esc` 停止

## 检查要点

- 窗口1应该显示：`CDP 端口: 127.0.0.1:9222`
- 窗口2应该显示：`CDP 端口: 127.0.0.1:9223`
- 两个窗口应该绑定不同的浏览器窗口

## 如果还有问题

请在 PowerShell 中运行以下命令检查环境：

```powershell
# 检查 Edge 浏览器是否存在
Test-Path "C:\Program Files\Microsoft\Edge\Application\msedge.exe"

# 检查 Python 是否可用
python --version

# 检查 fishing0.5.py 是否存在
Test-Path "E:\UsersData\Desktop\Project\fish\origin\fishing0.5.py"
```

如果以上任何命令返回 False 或错误，请告诉我具体的错误信息。
