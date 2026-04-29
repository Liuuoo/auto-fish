# 多账号启动器测试指南

## 📋 测试前准备

确保已安装所有依赖：
```bash
pip install opencv-python numpy pynput websocket-client
```

## 🚀 启动器测试步骤

### 方法1：使用启动器（推荐）

```bash
python launcher.py
```

然后按照提示操作：

1. **输入账号数量**
   ```
   请输入需要启动的账号数量 (1-5): 2
   ```
   输入 `2` 表示启动2个账号

2. **等待浏览器启动**
   - 启动器会自动启动2个 Edge 浏览器窗口
   - 账号1使用端口 9222
   - 账号2使用端口 9223

3. **登录账号**
   - 在第一个浏览器窗口中登录账号1
   - 在第二个浏览器窗口中登录账号2
   - 都进入钓鱼界面

4. **按 Enter 继续**
   - 启动器会自动打开2个命令行窗口
   - 每个窗口运行一个钓鱼脚本实例

5. **在每个钓鱼脚本窗口中操作**
   - 按 `F8` 绑定对应的浏览器窗口
   - 选择游戏标签页（输入编号）
   - 拖拽鼠标选择识别区域
   - 按 `F7` 开始钓鱼
   - 按 `Esc` 停止

### 方法2：手动测试单个账号

如果想先测试单个账号是否正常工作：

1. **启动浏览器**
   ```bash
   # 右键点击 start_edge_debug.ps1，选择"使用 PowerShell 运行"
   # 或者在 PowerShell 中运行：
   .\start_edge_debug.ps1
   ```

2. **启动钓鱼脚本**
   ```bash
   python fishing0.5.py --port 9222 --name "测试账号"
   ```

3. **操作**
   - 按 `F8` 绑定浏览器窗口
   - 选择游戏标签页
   - 拖拽选择识别区域
   - 按 `F7` 开始钓鱼

### 方法3：手动测试多个账号

如果启动器有问题，可以手动测试：

1. **启动第一个浏览器（端口 9222）**
   ```powershell
   $port = 9222
   $userDataDir = "$env:TEMP\chrome-fishing-$port"
   $edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
   Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=$port","--user-data-dir=`"$userDataDir`"","--disable-features=RendererCodeIntegrity"
   ```

2. **启动第二个浏览器（端口 9223）**
   ```powershell
   $port = 9223
   $userDataDir = "$env:TEMP\chrome-fishing-$port"
   $edgePath = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
   Start-Process -FilePath $edgePath -ArgumentList "--remote-debugging-port=$port","--user-data-dir=`"$userDataDir`"","--disable-features=RendererCodeIntegrity"
   ```

3. **在两个浏览器中登录账号**

4. **启动第一个钓鱼脚本**
   ```bash
   python fishing0.5.py --port 9222 --name Account1
   ```

5. **启动第二个钓鱼脚本（新的命令行窗口）**
   ```bash
   python fishing0.5.py --port 9223 --name Account2
   ```

## ✅ 验证测试成功

每个钓鱼脚本启动后应该显示：

```
=== 自动钓鱼脚本 0.5（CDP 注入版）===
实例名称: Account1
CDP 端口: 127.0.0.1:9222

先决条件：
  Chrome 启动时需带参数 --remote-debugging-port=9222
  推荐： chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-fishing-9222"
  pip install websocket-client

操作：F8 绑定窗口 → 选 tab → 拖框选区 → F7 启动/暂停 → ESC 停止/退出
```

预览窗口标题应该显示：
- `Fishing Preview - Account1`
- `Fishing Preview - Account2`

## ❌ 常见问题

### 问题1：启动器找不到 Edge 浏览器
**解决方法**：检查 Edge 是否安装在默认路径，或修改 `launcher.py` 中的 `edge_paths` 列表

### 问题2：CDP 连接失败
**解决方法**：
- 确保浏览器已启动并使用正确的端口
- 检查防火墙设置
- 确认端口没有被其他程序占用

### 问题3：窗口绑定失败
**解决方法**：
- 确保按 F8 时对应的浏览器窗口在前台
- 检查窗口类名是否为 `Chrome_WidgetWin_1`

### 问题4：启动器无法打开新的命令行窗口
**解决方法**：
- 在 Windows 上应该会自动打开新窗口
- 如果失败，手动打开命令行窗口运行钓鱼脚本

## 📊 测试检查清单

- [ ] 启动器能正常询问账号数量
- [ ] 能自动启动对应数量的浏览器
- [ ] 每个浏览器使用不同的端口和用户数据目录
- [ ] 能自动启动对应数量的钓鱼脚本
- [ ] 每个钓鱼脚本显示正确的实例名称和端口
- [ ] 预览窗口标题能区分不同账号
- [ ] 每个脚本能独立操作（F8, F7, Esc）
- [ ] 多个账号可以同时钓鱼，互不干扰

## 🎯 下一步

测试成功后，可以：
1. 继续完成代码模块化重构
2. 优化启动器的用户体验
3. 添加更多功能（如自动绑定窗口）
