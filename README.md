# auto-fish

浏览器游戏自动钓鱼辅助脚本。项目通过 Windows 窗口截图识别鱼漂和鱼影，并通过浏览器 DevTools Protocol 向已打开的游戏页面注入按键操作。

## 环境要求

- Windows 10/11
- Microsoft Edge 或 Chrome
- Python 3.12 或 3.13（仅源码运行或自行打包时需要）
- Git（仅克隆源码时需要）

源码运行所需 Python 依赖见 `requirements.txt`：

```bash
pip install -r requirements.txt
```

## 下载项目

```bash
git clone https://github.com/Liuuoo/auto-fish.git
cd auto-fish
```

## 运行方式

### 方案 1：使用已打包程序

这是推荐的日常使用方式。

1. 右键 `start_edge_debug.ps1`，选择“使用 PowerShell 运行”。
2. 在自动打开的浏览器窗口中进入目标游戏页面并登录。
3. 双击已打包的可执行文件，打开钓鱼识别程序。
4. 在程序提示下按 `F8` 绑定当前浏览器窗口。
5. 选择对应的浏览器 tab。
6. 在预览窗口中拖拽选择识别区域。
7. 按 `F7` 开始或暂停自动钓鱼。
8. 按 `Esc` 停止或退出。

如果系统禁止直接运行 PowerShell 脚本，可以改用 `StartEdge.bat` 启动浏览器调试窗口。

### 方案 2：从源码运行

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 启动带调试端口的浏览器：

```powershell
.\start_edge_debug.ps1
```

3. 在新打开的浏览器窗口中进入目标游戏页面并登录。

4. 启动识别脚本：

```bash
python fishing0.5.py
```

5. 按程序提示操作：

- `F8`：绑定当前浏览器窗口
- 选择对应的浏览器 tab
- 在预览窗口中拖拽选择识别区域
- `F7`：开始或暂停自动钓鱼
- `Esc`：停止或退出

## 打包可执行文件

项目包含 PyInstaller 配置文件，可按需打包：

```bash
pyinstaller fishing0.5.spec
```

生成的 `build/`、`dist/`、`build_debug/` 等目录是构建产物，不纳入 Git 仓库。

## 当前用到的接口

当前脚本实际使用的外部 API/协议如下：

- Chrome/Edge DevTools Protocol：`http://127.0.0.1:9222/json`，用于列出可连接的浏览器页面，并通过 `webSocketDebuggerUrl` 连接目标 tab。
- 目标游戏前端页面：用于识别当前游戏页面来源与浏览器存储上下文。
- 目标游戏物品接口：用于读取快捷栏工具和鱼竿耐久信息。

项目不会上传本地抓包资料、接口参考文档和构建产物。

## 问题记录与维护方案

历史问题按“问题索引 + 单问题解决文档”的形式维护，入口见 [troubleshooting/README.md](troubleshooting/README.md)。
