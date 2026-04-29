#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试启动器参数传递
"""
import sys
import subprocess
from pathlib import Path

print("测试启动器参数传递")
print("=" * 50)

# 测试参数
test_cases = [
    {"port": 9222, "name": "Account1"},
    {"port": 9223, "name": "Account2"},
]

script_path = Path(__file__).parent / "fishing0.5.py"

for test in test_cases:
    port = test["port"]
    name = test["name"]

    print(f"\n测试 {name} (端口 {port}):")

    # 构建命令
    args = [
        sys.executable,
        str(script_path),
        "--port", str(port),
        "--name", name,
        "--auto-bind",
    ]

    print(f"命令: {' '.join(args)}")

    # 测试命令（不实际运行，只显示）
    cmd_str = ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in args)
    print(f"完整命令: {cmd_str}")
    print()

print("=" * 50)
print("如果要实际测试，请手动运行上面的命令")
