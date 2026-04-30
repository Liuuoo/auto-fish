# 多账号钓鱼机器人 - 手动启动指南

本指南提供完整的手动启动流程，适用于批处理脚本无法正常运行的情况。

## 📋 前置要求

- ✅ 已安装 Microsoft Edge 浏览器
- ✅ 已安装 Python 3.12 或 3.13
- ✅ 已安装依赖：`pip install opencv-python numpy pynput websocket-client`

## 🚀 完整启动流程

### 步骤1：打开 PowerShell

按 `Win + X`，选择"Windows PowerShell"

### 步骤2：启动浏览器

**一次性复制以下所有命令，粘贴到 PowerShell 中：**

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

### 步骤3：在浏览器中登录账号

在两个浏览器窗口中分别登录账号，进入钓鱼界面

### 步骤4：启动钓鱼脚本

#### 4.1 启动第一个钓鱼脚本

按 `Win + R`，输入 `cmd`，回车

在命令行窗口中运行：
```bash
cd "E:\UsersData\Desktop\Project\fish\origin"
python fishing0.5.py --port 9222 --name Account1 --auto-bind
```

**选择窗口：**
脚本会显示所有浏览器窗口：
```
检测到 2 个浏览器窗口：
  [0] HWND=0x... | SatWorld Avatar - 个人 - Microsoft Edge
  [1] HWND=0x... | SatWorld Avatar - 个人 - Microsoft Edge

提示：端口 9222 建议选择对应的浏览器窗口
请输入窗口编号 (0-1): 
```

**输入 `0` 选择第一个窗口**

#### 4.2 启动第二个钓鱼脚本

再次按 `Win + R`，输入 `cmd`，回车

在新的命令行窗口中运行：
```bash
cd "E:\UsersData\Desktop\Project\fish\origin"
python fishing0.5.py --port 9223 --name Account2 --auto-bind
```

**选择窗口：**
脚本会显示所有浏览器窗口，**输入 `1` 选择第二个窗口**

### 步骤5：开始钓鱼

在每个预览窗口中：
1. 拖拽选择识别区域
2. 按 `F7` 开始钓鱼
3. 按 `Esc` 停止

## ✅ 检查要点

### 窗口1（Account1）应该显示：
```
实例名称: Account1
CDP 端口: 127.0.0.1:9222

=== [1/2] 选择浏览器窗口 ===
[已选择] 窗口 0
  HWND=0x... | SatWorld Avatar - 个人 - Microsoft Edge

=== [2/2] 连接 CDP 127.0.0.1:9222（用于注入按键）===
[CDP] 已连接 SatWorld Avatar
```

### 窗口2（Account2）应该显示：
```
实例名称: Account2
CDP 端口: 127.0.0.1:9223

=== [1/2] 选择浏览器窗口 ===
[已选择] 窗口 1
  HWND=0x... | SatWorld Avatar - 个人 - Microsoft Edge

=== [2/2] 连接 CDP 127.0.0.1:9223（用于注入按键）===
[CDP] 已连接 SatWorld Avatar
```

### 关键检查：
- ✅ 两个窗口显示不同的端口号（9222 vs 9223）
- ✅ 两个窗口绑定了不同的 HWND
- ✅ 两个窗口都成功连接 CDP
- ✅ 预览窗口标题不同（Account1 vs Account2）

## 🔧 常见问题

### Q1: 找不到 Edge 浏览器

**错误信息：** `系统找不到指定的文件`

**解决方法：**
在 PowerShell 中运行以下命令查找 Edge 路径：
```powershell
# 检查 32位版本
Test-Path "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 检查 64位版本
Test-Path "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
```

找到正确的路径后，修改启动命令中的 `$edgePath` 变量。

### Q2: CDP 连接失败

**错误信息：** `无法连接 CDP 127.0.0.1:9222`

**解决方法：**
1. 确认浏览器已启动并使用了正确的端口
2. 检查防火墙是否阻止了端口
3. 确认浏览器启动参数包含 `--remote-allow-origins=*`

### Q3: 两个脚本绑定了同一个窗口

**解决方法：**
- 在启动第一个脚本时选择窗口 0
- 在启动第二个脚本时选择窗口 1
- 确保选择了不同的窗口编号

### Q4: Python 环境问题

**检查 Python 环境：**
```bash
python --version
pip list | grep -E "opencv|numpy|pynput|websocket"
```

**安装缺失的依赖：**
```bash
pip install opencv-python numpy pynput websocket-client
```

## 📝 添加更多账号

如果需要第3个、第4个账号：

### 启动第3个浏览器（端口 9224）
```powershell
Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=9224","--user-data-dir=`"$env:TEMP\chrome-fishing-9224`"","--remote-allow-origins=*","--disable-features=RendererCodeIntegrity"
```

### 启动第3个钓鱼脚本
```bash
python fishing0.5.py --port 9224 --name Account3 --auto-bind
```

选择窗口时输入 `2`（第三个窗口）

## 💡 提示

1. **启动顺序很重要**：先启动浏览器，再启动钓鱼脚本
2. **窗口选择**：确保每个脚本选择不同的窗口编号
3. **端口对应**：端口 9222 对应第1个窗口，端口 9223 对应第2个窗口
4. **资源占用**：每个账号约占用 500MB-1GB 内存
5. **网络稳定**：建议使用稳定的网络连接

## 📊 端口分配表

| 账号 | CDP端口 | 窗口编号 | 用户数据目录 |
|------|---------|---------|-------------|
| Account1 | 9222 | 0 | %TEMP%\chrome-fishing-9222 |
| Account2 | 9223 | 1 | %TEMP%\chrome-fishing-9223 |
| Account3 | 9224 | 2 | %TEMP%\chrome-fishing-9224 |
| Account4 | 9225 | 3 | %TEMP%\chrome-fishing-9225 |
| Account5 | 9226 | 4 | %TEMP%\chrome-fishing-9226 |
