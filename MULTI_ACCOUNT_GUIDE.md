# 多账号钓鱼机器人使用指南

本指南介绍如何使用多账号模式同时运行多个钓鱼账号。

## ✨ 功能特性

- 👥 **多账号支持** - 同时运行 1-5 个账号
- ⌨️ **独立快捷键** - 每个账号有独立的快捷键，避免冲突
- 🔄 **顺序启动** - 逐个启动账号，避免端口冲突
- 🎯 **自动绑定** - 自动选择浏览器窗口
- 📊 **独立运行** - 每个账号完全独立，互不干扰

## 📋 系统要求

- Windows 10/11
- Python 3.12 或 3.13
- Microsoft Edge 浏览器
- 依赖库：`opencv-python`, `numpy`, `pynput`, `websocket-client`

## 🚀 快速开始

### 方法1：一键启动（推荐）

1. **安装依赖**
   ```bash
   pip install opencv-python numpy pynput websocket-client
   ```

2. **运行启动脚本**
   
   右键点击 `start_multi_account.ps1`，选择"使用 PowerShell 运行"

3. **按照提示操作**
   - 输入需要启动的账号数量（1-5）
   - 等待浏览器自动启动
   - 在浏览器中登录账号
   - 在钓鱼脚本窗口中选择浏览器窗口（输入编号）
   - 拖拽选择识别区域
   - 按对应的快捷键开始钓鱼

### 方法2：手动启动

详细步骤请参考 [MANUAL_START.md](MANUAL_START.md)

## ⌨️ 快捷键说明

每个账号有独立的快捷键：

| 账号 | 端口 | 启动/暂停 | 绑定窗口 | 停止/退出 |
|------|------|----------|---------|----------|
| Account1 | 9222 | **F7** | F8 | Esc |
| Account2 | 9223 | **F9** | F8 | Esc |
| Account3 | 9224 | **F10** | F8 | Esc |
| Account4 | 9225 | **F11** | F8 | Esc |
| Account5 | 9226 | **F12** | F8 | Esc |

**说明：**
- **启动/暂停键**：第一次按启动，第二次按暂停，第三次按继续
- **F8**：绑定浏览器窗口（仅手动模式）
- **Esc**：停止钓鱼或退出程序

## 🔧 浏览器路径配置

### 自动查找

启动脚本会自动查找 Edge 浏览器，支持以下路径：
- `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`（32位）
- `C:\Program Files\Microsoft\Edge\Application\msedge.exe`（64位）
- `%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe`（用户安装）

### 手动指定

如果自动查找失败，可以手动修改 `start_multi_account.ps1` 中的路径：

1. 右键点击 `start_multi_account.ps1`，选择"编辑"
2. 找到以下代码：
   ```powershell
   $edgePaths = @(
       "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
       "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
       "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
   )
   ```
3. 在数组开头添加你的 Edge 路径：
   ```powershell
   $edgePaths = @(
       "你的Edge浏览器路径\msedge.exe",  # 添加这一行
       "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
       "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
       "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
   )
   ```

### 查找 Edge 路径

在 PowerShell 中运行：
```powershell
# 方法1：使用 where 命令
where.exe msedge.exe

# 方法2：检查常见路径
Test-Path "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
Test-Path "C:\Program Files\Microsoft\Edge\Application\msedge.exe"

# 方法3：查看 Edge 快捷方式属性
# 右键桌面上的 Edge 图标 → 属性 → 目标
```

## 📖 使用流程

### 完整流程

1. **启动脚本** - 右键运行 `start_multi_account.ps1`
2. **输入数量** - 输入需要启动的账号数量（1-5）
3. **对于每个账号：**
   - 脚本自动启动浏览器
   - 在浏览器中登录账号
   - 按 Enter 继续
   - 脚本自动启动钓鱼程序
   - 在钓鱼程序中选择浏览器窗口（输入编号）
   - 拖拽选择识别区域
   - 按对应的快捷键开始钓鱼
4. **开始钓鱼** - 所有账号设置完成后开始钓鱼

### 自动暂停

脚本会在以下情况自动暂停：
- **大空投** - 检测到大空投弹窗时自动暂停
- **无体力** - 检测到无体力弹窗时自动暂停（并点击 Buy Energy）
- **无鱼竿** - 快捷栏没有可用鱼竿时自动暂停

暂停后，脚本会提示你按对应的快捷键继续。例如：
```
[空投] 发现大空投，请手动处理任务；脚本已暂停，处理完成后按 F9 继续
[体力] 检测到无体力，已点击 Buy Energy；脚本已暂停，处理完成后按 F9 继续
```

## ❓ 常见问题

### Q1: 找不到 Edge 浏览器

**错误信息：** `ERROR: Microsoft Edge not found`

**解决方法：**
1. 确认已安装 Microsoft Edge
2. 使用上面的方法查找 Edge 路径
3. 手动修改启动脚本中的路径

### Q2: CDP 连接失败

**错误信息：** `无法连接 CDP 127.0.0.1:9222`

**解决方法：**
1. 确认浏览器已启动并使用了正确的端口
2. 检查防火墙是否阻止了端口
3. 确认浏览器启动参数包含 `--remote-allow-origins=*`

### Q3: 两个脚本绑定了同一个窗口

**解决方法：**
- 使用顺序启动模式（`start_multi_account.ps1` 已实现）
- 在启动第一个脚本时选择窗口 0
- 在启动第二个脚本时选择窗口 1
- 确保选择了不同的窗口编号

### Q4: 按键冲突

**问题：** 按 F7 时两个账号都启动了

**解决方法：**
- 每个账号使用不同的快捷键
- Account1 用 F7，Account2 用 F9，Account3 用 F10...
- 查看上面的快捷键对照表

### Q5: 端口识别混乱

**问题：** py1 绑定 9222 却识别到 9223

**解决方法：**
- 使用顺序启动模式（`start_multi_account.ps1` 已实现）
- 不要同时启动多个浏览器和脚本
- 等待每个账号完全设置好后再启动下一个

## 📊 端口分配表

| 账号 | CDP端口 | 建议窗口编号 | 用户数据目录 | 快捷键 |
|------|---------|-------------|-------------|--------|
| Account1 | 9222 | 0 | %TEMP%\chrome-fishing-9222 | F7 |
| Account2 | 9223 | 1 | %TEMP%\chrome-fishing-9223 | F9 |
| Account3 | 9224 | 2 | %TEMP%\chrome-fishing-9224 | F10 |
| Account4 | 9225 | 3 | %TEMP%\chrome-fishing-9225 | F11 |
| Account5 | 9226 | 4 | %TEMP%\chrome-fishing-9226 | F12 |

## 💡 使用技巧

1. **启动顺序很重要** - 先启动浏览器，再启动钓鱼脚本
2. **窗口选择** - 确保每个脚本选择不同的窗口编号
3. **端口对应** - 端口 9222 对应第1个窗口，端口 9223 对应第2个窗口
4. **资源占用** - 每个账号约占用 500MB-1GB 内存
5. **网络稳定** - 建议使用稳定的网络连接
6. **快捷键记忆** - 可以在每个预览窗口标题看到账号名称

## 🗂️ 相关文件

- `start_multi_account.ps1` - 一键启动脚本（推荐使用）
- `fishing0.5.py` - 主程序（已支持多账号和独立快捷键）
- `MANUAL_START.md` - 手动启动指南（备用方法）
- `README.md` - 项目主文档

## 📝 版本说明

- **单账号版本** - `main` 分支，标签 `v1.0-single-thread`
- **多账号版本** - `refactor/multi-account` 分支（当前）

## 🙏 反馈与支持

如果遇到问题，请：
1. 查看本文档的常见问题部分
2. 查看 `MANUAL_START.md` 获取详细步骤
3. 检查 git 提交记录了解最新更新

祝你钓鱼愉快！🎣
