#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多账号钓鱼机器人启动器

功能：
1. 询问用户需要启动几个账号
2. 自动启动对应数量的浏览器（不同端口）
3. 自动启动对应数量的钓鱼脚本进程
"""
import os
import sys
import time
import subprocess
from pathlib import Path


def get_account_count():
    """询问用户需要启动几个账号"""
    print("=" * 50)
    print("多账号钓鱼机器人启动器")
    print("=" * 50)
    print()

    while True:
        try:
            count = input("请输入需要启动的账号数量 (1-5): ").strip()
            count = int(count)
            if 1 <= count <= 5:
                return count
            else:
                print("❌ 请输入 1-5 之间的数字")
        except ValueError:
            print("❌ 请输入有效的数字")
        except KeyboardInterrupt:
            print("\n\n已取消")
            sys.exit(0)


def start_browser(port, account_name):
    """启动浏览器"""
    print(f"[{account_name}] 启动浏览器 (端口 {port})...")

    # 查找 Edge 浏览器路径
    edge_paths = [
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]

    edge_path = None
    for path in edge_paths:
        if os.path.exists(path):
            edge_path = path
            break

    if not edge_path:
        print(f"❌ [{account_name}] 未找到 Edge 浏览器")
        return False

    # 启动浏览器
    user_data_dir = os.path.expandvars(f"%TEMP%\\chrome-fishing-{port}")
    args = [
        edge_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--remote-allow-origins=*",  # 允许 CDP 连接
        "--disable-features=RendererCodeIntegrity",
    ]

    try:
        subprocess.Popen(args,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        print(f"✅ [{account_name}] 浏览器已启动")
        return True
    except Exception as e:
        print(f"❌ [{account_name}] 启动浏览器失败: {e}")
        return False


def start_fishing_bot(port, account_name):
    """启动钓鱼脚本"""
    print(f"[{account_name}] 启动钓鱼脚本...")

    script_path = Path(__file__).parent / "fishing0.5.py"
    if not script_path.exists():
        print(f"❌ [{account_name}] 未找到 fishing0.5.py")
        return None

    # 构建命令
    cmd = f'python "{script_path}" --port {port} --name {account_name} --auto-bind'

    try:
        # 在新的命令行窗口中启动
        if sys.platform == "win32":
            # 使用 start 命令在新窗口中运行
            subprocess.Popen(
                f'start "Fishing Bot - {account_name}" cmd /k {cmd}',
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            args = [
                sys.executable,
                str(script_path),
                "--port", str(port),
                "--name", account_name,
                "--auto-bind",
            ]
            subprocess.Popen(args)

        print(f"✅ [{account_name}] 钓鱼脚本已启动")
        print(f"   命令: {cmd}")
        return True
    except Exception as e:
        print(f"❌ [{account_name}] 启动钓鱼脚本失败: {e}")
        return None


def main():
    """主函数"""
    # 获取账号数量
    count = get_account_count()

    print()
    print(f"准备启动 {count} 个账号...")
    print()

    # 基础端口
    base_port = 9222

    # 启动浏览器
    print("=" * 50)
    print("第1步：启动浏览器")
    print("=" * 50)
    print()

    for i in range(count):
        port = base_port + i
        account_name = f"Account{i+1}"
        start_browser(port, account_name)
        time.sleep(1)  # 避免同时启动太多进程

    print()
    print("✅ 所有浏览器已启动")
    print()
    print("=" * 50)
    print("第2步：登录账号")
    print("=" * 50)
    print()
    print("请在每个浏览器窗口中：")
    print("  1. 访问游戏网站")
    print("  2. 登录对应的账号")
    print("  3. 进入钓鱼界面")
    print()
    input("完成后按 Enter 继续...")

    # 启动钓鱼脚本
    print()
    print("=" * 50)
    print("第3步：启动钓鱼脚本")
    print("=" * 50)
    print()

    processes = []
    for i in range(count):
        port = base_port + i
        account_name = f"Account{i+1}"
        process = start_fishing_bot(port, account_name)
        if process:
            processes.append(process)
        time.sleep(1)

    print()
    print("=" * 50)
    print("✅ 所有账号已启动！")
    print("=" * 50)
    print()
    print("操作说明：")
    print("  1. 在每个钓鱼脚本窗口中按 F8 绑定浏览器窗口")
    print("  2. 选择游戏标签页")
    print("  3. 拖拽选择识别区域")
    print("  4. 按 F7 开始钓鱼")
    print("  5. 按 Esc 停止")
    print()
    print("按 Ctrl+C 退出启动器...")

    try:
        # 保持启动器运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n启动器已退出")
        print("注意：钓鱼脚本仍在运行，请在各自的窗口中按 Esc 停止")


if __name__ == "__main__":
    main()
