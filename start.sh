#!/bin/bash
# ========================================
# Fishing Bot - One-Click Startup (macOS)
# 不杀已有浏览器，直接启动调试窗口 + 钓鱼脚本
# ========================================

PORT=9222
USER_DATA_DIR="$HOME/.chrome-fishing-9222"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/fishing_mac.py"

# ---------- 找浏览器 ----------
BROWSER_PATH=""
for path in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" \
    "/Applications/Chromium.app/Contents/MacOS/Chromium"; do
    if [ -f "$path" ]; then
        BROWSER_PATH="$path"
        break
    fi
done

if [ -z "$BROWSER_PATH" ]; then
    echo "ERROR: No supported browser found" >&2
    exit 1
fi

# ---------- 启动调试浏览器（如未运行） ----------
if ! curl -s "http://127.0.0.1:$PORT/json" > /dev/null 2>&1; then
    mkdir -p "$USER_DATA_DIR"
    "$BROWSER_PATH" \
        --remote-debugging-port="$PORT" \
        --user-data-dir="$USER_DATA_DIR" \
        --remote-allow-origins=\* \
        --no-first-run \
        --no-default-browser-check \
        > /dev/null 2>&1 &
    sleep 2
fi

# ---------- 启动钓鱼脚本 ----------
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "ERROR: fishing_mac.py not found" >&2
    exit 1
fi

osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR' && python3 '$PYTHON_SCRIPT'\""

# 不等待，直接退出
