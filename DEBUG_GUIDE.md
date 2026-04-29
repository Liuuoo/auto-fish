# 启动器调试指南

## 问题诊断

你遇到的问题：
1. 两个脚本都连接到 9222 端口
2. CDP 连接仍然失败（403 Forbidden）

## 可能的原因

### 原因1：浏览器是手动启动的
如果你手动启动了浏览器（例如双击 start_edge_debug.ps1），那么：
- 浏览器只会监听 9222 端口
- 没有 `--remote-allow-origins=*` 参数
- 启动器无法启动新的浏览器实例

**解决方法**：
1. 关闭所有 Edge 浏览器
2. 只使用 `python launcher.py` 启动

### 原因2：启动器没有正确启动浏览器
检查启动器输出，应该看到：
```
[Account1] 启动浏览器 (端口 9222)...
✅ [Account1] 浏览器已启动
[Account2] 启动浏览器 (端口 9223)...
✅ [Account2] 浏览器已启动
```

如果没有看到这些信息，说明浏览器启动失败。

### 原因3：Windows 命令行参数传递问题
在 Windows 上，通过 `cmd /c start` 启动程序时，参数传递可能有问题。

## 调试步骤

### 步骤1：手动测试浏览器启动

在 PowerShell 中运行：

```powershell
# 测试账号1（端口 9222）
$port = 9222
$userDataDir = "$env:TEMP\chrome-fishing-$port"
$edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"

Start-Process -FilePath $edgePath -ArgumentList @(
    "--remote-debugging-port=$port",
    "--user-data-dir=`"$userDataDir`"",
    "--remote-allow-origins=*",
    "--disable-features=RendererCodeIntegrity"
)
```

然后测试 CDP 连接：
```bash
curl http://127.0.0.1:9222/json
```

应该返回 JSON 数据，而不是错误。

### 步骤2：手动测试钓鱼脚本

```bash
python fishing0.5.py --port 9222 --name Account1 --auto-bind
```

应该看到：
```
=== 自动钓鱼脚本 0.5（CDP 注入版）===
实例名称: Account1
CDP 端口: 127.0.0.1:9222
```

### 步骤3：检查端口占用

```bash
netstat -ano | findstr :9222
netstat -ano | findstr :9223
```

应该看到两个不同的端口都在监听。

## 临时解决方案

如果启动器有问题，可以手动启动：

### 1. 启动浏览器（PowerShell）

```powershell
# 账号1
$port = 9222
$userDataDir = "$env:TEMP\chrome-fishing-$port"
$edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=$port","--user-data-dir=`"$userDataDir`"","--remote-allow-origins=*","--disable-features=RendererCodeIntegrity"

# 账号2
$port = 9223
$userDataDir = "$env:TEMP\chrome-fishing-$port"
Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=$port","--user-data-dir=`"$userDataDir`"","--remote-allow-origins=*","--disable-features=RendererCodeIntegrity"
```

### 2. 登录账号

在两个浏览器窗口中分别登录账号

### 3. 启动钓鱼脚本（两个命令行窗口）

窗口1：
```bash
python fishing0.5.py --port 9222 --name Account1 --auto-bind
```

窗口2：
```bash
python fishing0.5.py --port 9223 --name Account2 --auto-bind
```

## 预期结果

每个钓鱼脚本应该显示：

**窗口1：**
```
=== 自动钓鱼脚本 0.5（CDP 注入版）===
实例名称: Account1
CDP 端口: 127.0.0.1:9222

=== [1/2] 自动绑定浏览器窗口 ===
[自动绑定] 已绑定第一个浏览器窗口
  HWND=0x... | SatWorld Avatar - 个人

=== [2/2] 连接 CDP 127.0.0.1:9222（用于注入按键）===
[自动匹配] 标题包含 'SatWorld Avatar - 个人'：SatWorld Avatar
[成功] CDP 已连接
```

**窗口2：**
```
=== 自动钓鱼脚本 0.5（CDP 注入版）===
实例名称: Account2
CDP 端口: 127.0.0.1:9223

=== [1/2] 自动绑定浏览器窗口 ===
[自动绑定] 已绑定第一个浏览器窗口
  HWND=0x... | SatWorld Avatar - 个人

=== [2/2] 连接 CDP 127.0.0.1:9223（用于注入按键）===
[自动匹配] 标题包含 'SatWorld Avatar - 个人'：SatWorld Avatar
[成功] CDP 已连接
```

注意端口号应该不同（9222 vs 9223）。

## 下一步

如果手动启动可以正常工作，说明问题在启动器的浏览器启动部分。
我会修复启动器的浏览器启动逻辑。
