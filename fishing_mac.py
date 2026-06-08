#!/usr/bin/env python3
"""
auto-fish macOS 版本
====================
基于原 Windows 版 fishing0.5.py 的 macOS 移植。
主要改动：
  - 窗口截图：macOS Quartz/CoreGraphics 替代 Win32 GDI
  - 窗口枚举：CGWindowListCopyWindowInfo 替代 EnumWindows
  - 声音提示：macOS afplay / printf('\a') 替代 winsound
  - 移除 DPI 感知（macOS 不需要）
  - 启动脚本：start.sh 替代 start.ps1

CDP 按键注入、鱼漂识别、鱼影检测等核心逻辑与原版一致。
"""

import asyncio
import json
import os
import re
import sys
import threading
import time
import random
import urllib.error
import urllib.parse
import urllib.request
import subprocess
from pathlib import Path

import cv2
import numpy as np
from pynput import keyboard

# ---------- macOS 专用模块 ----------
try:
    import Quartz
    _QUARTZ_AVAILABLE = True
except ImportError:
    Quartz = None
    _QUARTZ_AVAILABLE = False
    print("[警告] 缺少 pyobjc-framework-Quartz，窗口截图功能不可用")
    print("       安装：pip3 install pyobjc-framework-Quartz")

try:
    import mss
    _MSS_AVAILABLE = True
except ImportError:
    mss = None
    _MSS_AVAILABLE = False
    print("[警告] 缺少 mss，窗口截图功能不可用")
    print("       安装：pip3 install mss")

try:
    import websocket  # pip install websocket-client
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    websocket = None
    _WEBSOCKET_AVAILABLE = False

# ---------- Work API（可选）----------
try:
    WORK_DIR = Path(__file__).resolve().parent.parent / "work"
    if WORK_DIR.exists():
        sys.path.insert(0, str(WORK_DIR))
    from browser_session import BrowserSession as ApiBrowserSession
    from satworld_client import SatWorldClient as ApiSatWorldClient
    _WORK_API_AVAILABLE = True
except Exception:
    ApiBrowserSession = None
    ApiSatWorldClient = None
    _WORK_API_AVAILABLE = False

# ---------- 装备制作模块 ----------
try:
    from modules.crafting import CraftingManager
    _CRAFTING_AVAILABLE = True
except Exception as e:
    CraftingManager = None
    _CRAFTING_AVAILABLE = False
    print(f"[警告] 装备制作模块导入失败: {e}")


# ============================================================
# 常量（与原版一致）
# ============================================================
PREVIEW_WINDOW_NAME = "Fishing Preview"

CAPTURE_REGION = {"x": 0, "y": 0, "width": 355, "height": 159}

FISH_TRACK_RADIUS = 90
FLOAT_BOX_PADDING = 2
FLOAT_BOX_MIN_SIZE = 14
FLOAT_BOX_MAX_SIZE = 70
FLOAT_BOX_TRIGGER_THICKNESS = 5
FLOAT_CONFIRM_BOX_PADDING = 16
FLOAT_CONFIRM_BOX_THICKNESS = 6
FLOAT_MIN_AREA = 50
FISH_MIN_AREA = 25
FISH_BRIGHTNESS_DROP = 12
CAST_BITE_DETECTION_DELAY = 2.0
AIR_DROP_REWARD_FILE = "rewards.txt"
HIDDEN_AIRDROP_FILE = "hidden.txt"
NO_ENERGY_FILE = "noEnergy.txt"
AIR_DROP_CDP_TIMEOUT = 0.8
AIR_DROP_HANDLE_DELAY = 0.2
ROD_SWITCH_KEY_PRESSES = 2
ROD_SWITCH_PRE_KEY_DELAY = (0.16, 0.24)
ROD_SWITCH_KEY_INTERVAL = (0.08, 0.12)
ROD_SWITCH_SETTLE_DELAY = 0.8

# F 键的 CDP 描述
KEY_F = {"vk": 0x46, "code": "KeyF", "key": "f"}
KEY_DIGITS = {
    slot: {"vk": 0x30 + slot, "code": f"Digit{slot}", "key": str(slot)}
    for slot in range(1, 6)
}

# CDP
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222
API_USER_ITEM_URL = "https://api.satworld.io/game/user-item"
TOOL_SINGLE_TYPE_ORDER = {
    "FishingPole": 0,
    "Axe": 1,
    "Pickaxe": 2,
}
TOOL_TEXT_MARKERS = ("rod", "fishing", "axe", "pickaxe", "钓", "竿", "斧", "镐")


# ============================================================
# 全局状态
# ============================================================
running = False
paused = False
should_exit = False
preview_window_pinned = False

TARGET_WINDOW_ID = None   # macOS: CGWindowID (int)
TARGET_WINDOW_INFO = None # macOS: 窗口信息 dict

dragging = False
drag_start_x = 0
drag_start_y = 0
temp_region = None

MOUSE_PARAM = {"scale": 1.0, "client_w": 0, "client_h": 0}
CURRENT_ROD_SLOT = None
LAST_ROD_SLOTS = None
ROD_EXPECTED_DURABILITY = None
SELECTED_AUTH_ADDRESS = None

_cdp_ws = None
_cdp_msg_id = 0
_cdp_lock = threading.Lock()

# 装备制作
crafting_manager = None
crafting_task = None

# mss 实例（复用以提高性能）
_mss_instance = None


def _get_mss():
    global _mss_instance
    if _mss_instance is None and _MSS_AVAILABLE:
        _mss_instance = mss.MSS()
    return _mss_instance


# ============================================================
# 基础工具（与原版一致）
# ============================================================
def random_delay(a, b):
    return random.uniform(a, b)


def gaussian_delay(a, b):
    center = (a + b) / 2
    sigma = (b - a) / 6
    return clamp(random.gauss(center, sigma), a, b)


def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def _clip_box(box, width, height):
    l, t, r, b = box
    l = int(clamp(l, 0, width))
    t = int(clamp(t, 0, height))
    r = int(clamp(r, 0, width))
    b = int(clamp(b, 0, height))
    if r < l:
        r = l
    if b < t:
        b = t
    return l, t, r, b


def _square_box_from_center(center, side, width, height):
    cx, cy = center
    side = int(round(clamp(side, 1, max(width, height))))
    l = int(round(cx - side / 2))
    t = int(round(cy - side / 2))
    r = l + side
    b = t + side

    if l < 0:
        r -= l
        l = 0
    if t < 0:
        b -= t
        t = 0
    if r > width:
        l -= r - width
        r = width
    if b > height:
        t -= b - height
        b = height
    return _clip_box((l, t, r, b), width, height)


def _offset_box(box, dx, dy, width, height):
    l, t, r, b = box
    return _clip_box((l - dx, t - dy, r - dx, b - dy), width, height)


def _expand_box(box, padding, width, height):
    l, t, r, b = box
    return _clip_box((l - padding, t - padding, r + padding, b + padding), width, height)


def _draw_box_border(target, box, color, thickness):
    l, t, r, b = box
    if r - l <= 1 or b - t <= 1:
        return
    cv2.rectangle(target, (l, t), (r - 1, b - 1), color, thickness)


def _strip_chrome_suffix(title):
    for suffix in (" - Google Chrome", " - Microsoft​ Edge", " - Microsoft Edge",
                   " - Chromium", " - Brave"):
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


def clamp_region_to_client(cw, ch):
    CAPTURE_REGION["width"] = clamp(CAPTURE_REGION["width"], 20, max(20, cw))
    CAPTURE_REGION["height"] = clamp(CAPTURE_REGION["height"], 20, max(20, ch))
    CAPTURE_REGION["x"] = clamp(CAPTURE_REGION["x"], 0, max(0, cw - CAPTURE_REGION["width"]))
    CAPTURE_REGION["y"] = clamp(CAPTURE_REGION["y"], 0, max(0, ch - CAPTURE_REGION["height"]))


# ============================================================
# macOS 窗口管理（替代 Win32 user32/gdi32）
# ============================================================

def list_browser_windows():
    """列出所有浏览器窗口（macOS Quartz 版本）"""
    if not _QUARTZ_AVAILABLE:
        print("[错误] Quartz 不可用，无法枚举窗口")
        return []

    results = []
    try:
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        for w in window_list:
            owner = w.get('kCGWindowOwnerName', '')
            name = w.get('kCGWindowName', '')
            # 只保留有标题的浏览器窗口
            if not name:
                continue
            if any(browser in owner for browser in
                   ('Chrome', 'Edge', 'Chromium', 'Brave', 'Google Chrome')):
                # 过滤掉一些 Chrome 内部窗口
                if name in ('', 'Google Chrome', 'Microsoft Edge'):
                    continue
                window_id = w.get('kCGWindowNumber', 0)
                results.append((window_id, name, w))
    except Exception as e:
        print(f"[错误] 枚举窗口失败: {e}")

    return results


def is_window_ready(window_id):
    """检查窗口是否仍然可用（未被关闭）"""
    if window_id is None:
        return False
    try:
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        for w in window_list:
            if w.get('kCGWindowNumber') == window_id:
                return True
    except Exception:
        pass
    return False


def is_window_minimized(window_info):
    """检查窗口是否最小化（macOS: 检查是否在屏幕列表中）"""
    if window_info is None:
        return True
    # macOS: 如果窗口不在屏幕列表中，可能是最小化了
    try:
        window_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly,
            Quartz.kCGNullWindowID
        )
        wid = window_info.get('kCGWindowNumber', 0)
        for w in window_list:
            if w.get('kCGWindowNumber') == wid:
                return False  # 在屏幕上，未最小化
    except Exception:
        pass
    return True


def get_window_title(window_info):
    """获取窗口标题"""
    if window_info is None:
        return ""
    return window_info.get('kCGWindowName', '')


def get_window_bounds(window_info):
    """获取窗口在屏幕上的位置和大小"""
    if window_info is None:
        return None
    bounds = window_info.get('kCGWindowBounds', {})
    return {
        'x': int(bounds.get('X', 0)),
        'y': int(bounds.get('Y', 0)),
        'width': int(bounds.get('Width', 0)),
        'height': int(bounds.get('Height', 0)),
    }


def pick_target_window():
    """用户按 F8 绑定浏览器窗口"""
    global TARGET_WINDOW_ID, TARGET_WINDOW_INFO

    print("\n=== [1/2] 绑定浏览器窗口（用于截图识别）===")
    print("把目标浏览器窗口切到前台，按 F8 绑定。按 Q 退出。\n")

    windows = list_browser_windows()
    if windows:
        print("当前检测到的 Chrome/Edge 窗口：")
        for wid, name, _ in windows:
            print(f"  WindowID={wid} | {name[:80]}")
    else:
        print("当前未检测到浏览器窗口；打开后再按 F8。")
    print()

    while TARGET_WINDOW_ID is None:
        if should_exit:
            return None
        time.sleep(0.1)

    return TARGET_WINDOW_ID


# ============================================================
# macOS 截图（替代 PrintWindow + GetDIBits）
# ============================================================

def capture_window_full(window_info):
    """捕获整个窗口内容（macOS 版本）

    使用 CGWindowListCreateImage 直接捕获窗口内容，
    这是最接近 Windows PrintWindow 的方式。
    """
    if window_info is None:
        return None, 0, 0

    window_id = window_info.get('kCGWindowNumber', 0)
    if not window_id:
        return None, 0, 0

    bounds = window_info.get('kCGWindowBounds', {})
    win_w = int(bounds.get('Width', 0))
    win_h = int(bounds.get('Height', 0))
    if win_w <= 0 or win_h <= 0:
        return None, 0, 0

    try:
        # 方法1: 使用 CGWindowListCreateImage 直接捕获窗口
        image = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull,
            Quartz.kCGWindowListOptionIncludingWindow,
            window_id,
            Quartz.kCGWindowImageBoundsIgnoreFraming | Quartz.kCGWindowImageNominalResolution
        )

        if image is None:
            # 方法2: 回退到 mss 屏幕截图 + 坐标裁剪
            return _capture_via_mss(window_info)

        width = Quartz.CGImageGetWidth(image)
        height = Quartz.CGImageGetHeight(image)
        bytes_per_row = Quartz.CGImageGetBytesPerRow(image)
        bits_per_pixel = Quartz.CGImageGetBitsPerPixel(image)

        data_provider = Quartz.CGImageGetDataProvider(image)
        data = Quartz.CGDataProviderCopyData(data_provider)

        if data is None:
            return _capture_via_mss(window_info)

        # CGImage 数据格式: BGRA 8bit (通常) 或 ARGB 8bit
        arr = np.frombuffer(data, dtype=np.uint8)

        if bits_per_pixel == 32:
            components = 4
        elif bits_per_pixel == 24:
            components = 3
        else:
            components = 4

        expected_width = bytes_per_row // components
        arr = arr.reshape((height, expected_width, components))
        arr = arr[:, :width, :]  # 裁剪掉行末填充

        # CGImage 通常是 BGRA 格式
        if components == 4:
            bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        else:
            bgr = arr

        return bgr, width, height

    except Exception as e:
        print(f"[截图] Quartz 捕获失败: {e}，回退到 mss")
        return _capture_via_mss(window_info)


def _capture_via_mss(window_info):
    """使用 mss 库的屏幕截图回退方案"""
    if not _MSS_AVAILABLE:
        return None, 0, 0

    try:
        bounds = window_info.get('kCGWindowBounds', {})
        x = int(bounds.get('X', 0))
        y = int(bounds.get('Y', 0))
        w = int(bounds.get('Width', 0))
        h = int(bounds.get('Height', 0))
        if w <= 0 or h <= 0:
            return None, 0, 0

        sct = _get_mss()
        if sct is None:
            return None, 0, 0

        monitor = {'left': x, 'top': y, 'width': w, 'height': h}
        screenshot = sct.grab(monitor)
        arr = np.array(screenshot)
        # mss 返回 BGRA
        bgr = cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR)
        return bgr, w, h

    except Exception as e:
        print(f"[截图] mss 也失败了: {e}")
        return None, 0, 0


def capture_window_client(window_info):
    """捕获窗口内容（与原版 capture_window_client 接口兼容）

    注意: macOS 上 CGWindowListCreateImage 捕获的是整个窗口（包含标题栏），
    与 Windows PrintWindow（仅客户区）不同。
    用户需要在预览窗口中手动选择合适的识别区域。
    """
    return capture_window_full(window_info)


# ============================================================
# macOS 声音提示（替代 winsound）
# ============================================================

def play_beep():
    """macOS 蜂鸣声"""
    try:
        # 优先使用系统蜂鸣
        print('\a', end='', flush=True)
    except Exception:
        pass


def play_sound_async():
    """异步播放提示音"""
    try:
        subprocess.Popen(['afplay', '/System/Library/Sounds/Glass.aiff'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except Exception:
        play_beep()


# ============================================================
# CDP 通信（与原版完全一致，这部分是跨平台的）
# ============================================================

def cdp_list_pages(host=CDP_HOST, port=CDP_PORT, timeout=2.0):
    url = f"http://{host}:{port}/json"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    return [t for t in data if t.get("type") == "page"]


def cdp_pick_target(window_title_hint="", host=CDP_HOST, port=CDP_PORT):
    """返回 CDP target dict 或 None"""
    print(f"\n=== [2/2] 连接 CDP {host}:{port}（用于注入按键）===")

    if not _WEBSOCKET_AVAILABLE:
        print("[错误] 缺少依赖 websocket-client：pip3 install websocket-client")
        return None

    try:
        pages = cdp_list_pages(host, port)
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接 CDP {host}:{port}：{e}")
        print(f"请确保 Chrome 启动时加了  --remote-debugging-port={port}")
        return None
    except Exception as e:
        print(f"[错误] CDP 列表拉取失败：{e}")
        return None

    if not pages:
        print("[错误] CDP 未列出任何 page target")
        return None

    hint = _strip_chrome_suffix(window_title_hint).strip()
    auto = None
    if hint:
        for t in pages:
            title = t.get("title", "")
            if hint and (hint in title or title in hint):
                auto = t
                break

    if auto:
        print(f"[自动匹配] 标题包含 {hint!r}：{auto.get('title', '')[:70]}")
        return auto

    print("请选择一个 tab：")
    for i, t in enumerate(pages):
        print(f"  [{i}] {t.get('title', '')[:70]}")
        print(f"       {t.get('url', '')[:70]}")

    while not should_exit:
        try:
            choice = input("编号 > ").strip()
        except EOFError:
            return None
        if not choice:
            continue
        try:
            idx = int(choice)
            if 0 <= idx < len(pages):
                return pages[idx]
        except ValueError:
            pass
        print("无效输入")
    return None


def cdp_connect(target, timeout=3.0):
    global _cdp_ws
    ws_url = target["webSocketDebuggerUrl"]
    ws = websocket.create_connection(ws_url, timeout=timeout)
    _cdp_ws = ws
    print(f"[CDP] 已连接 {target.get('title', '')[:70]}")
    return ws


def _cdp_raw_send(method, params=None):
    global _cdp_msg_id, _cdp_ws
    if _cdp_ws is None:
        return False
    with _cdp_lock:
        _cdp_msg_id += 1
        mid = _cdp_msg_id
        payload = json.dumps({"id": mid, "method": method, "params": params or {}})
        try:
            _cdp_ws.send(payload)
            return True
        except Exception as e:
            print(f"[CDP] 发送失败：{e}")
            return False


def _cdp_call(method, params=None, timeout=5.0):
    global _cdp_msg_id, _cdp_ws
    last_error = None

    for attempt in range(2):
        if _cdp_ws is None and not cdp_reconnect():
            break

        try:
            with _cdp_lock:
                _cdp_msg_id += 1
                mid = _cdp_msg_id
                payload = json.dumps({"id": mid, "method": method, "params": params or {}})
                _cdp_ws.settimeout(timeout)
                _cdp_ws.send(payload)

                while True:
                    raw = _cdp_ws.recv()
                    if not raw:
                        continue
                    message = json.loads(raw)
                    if message.get("id") == mid:
                        return message
        except Exception as e:
            last_error = e
            if attempt == 0 and cdp_reconnect():
                continue
            break

    print(f"[CDP] 调用 {method} 失败：{last_error}")
    return None


def cdp_evaluate(expression, await_promise=False, timeout=5.0):
    response = _cdp_call(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        },
        timeout=timeout,
    )
    if not isinstance(response, dict):
        return None
    if response.get("error"):
        return {"ok": False, "reason": "cdp_error", "error": response.get("error")}

    result = response.get("result") or {}
    if result.get("exceptionDetails"):
        return {
            "ok": False,
            "reason": "js_exception",
            "error": result.get("exceptionDetails"),
        }

    remote_result = result.get("result") or {}
    if "value" in remote_result:
        return remote_result.get("value")
    return {
        "ok": False,
        "reason": "missing_value",
        "result": remote_result,
    }


def _cdp_target_origin():
    target = _cdp_target_cache or {}
    url = str(target.get("url") or "").strip()
    if not url.startswith("http"):
        return "https://beta.satworld.io"
    parts = urllib.parse.urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return "https://beta.satworld.io"
    return f"{parts.scheme}://{parts.netloc}"


def _cdp_storage_id(timeout=5.0):
    frame_response = _cdp_call("Page.getFrameTree", timeout=timeout)
    if isinstance(frame_response, dict):
        frame_tree = (frame_response.get("result") or {}).get("frameTree") or {}
        frame = frame_tree.get("frame") or {}
        frame_id = frame.get("id")
        if frame_id:
            storage_key_response = _cdp_call(
                "Storage.getStorageKeyForFrame",
                {"frameId": frame_id},
                timeout=timeout,
            )
            if isinstance(storage_key_response, dict):
                storage_key = (storage_key_response.get("result") or {}).get("storageKey")
                if storage_key:
                    return {
                        "storageKey": storage_key,
                        "isLocalStorage": True,
                    }

    return {
        "securityOrigin": _cdp_target_origin(),
        "isLocalStorage": True,
    }


def cdp_get_local_storage_items(timeout=5.0):
    response = _cdp_call(
        "DOMStorage.getDOMStorageItems",
        {
            "storageId": _cdp_storage_id(timeout=timeout),
        },
        timeout=timeout,
    )
    if not isinstance(response, dict):
        return {}

    result = response.get("result") or {}
    entries = result.get("entries")
    if not isinstance(entries, list):
        return {}

    storage = {}
    for entry in entries:
        if isinstance(entry, list) and len(entry) >= 2:
            storage[str(entry[0])] = str(entry[1])
    return storage


_cdp_target_cache = None
_airdrop_reward_signature_cache = None
_hidden_airdrop_signature_cache = None
_no_energy_signature_cache = None


def cdp_reconnect():
    """断线重连。依赖上次使用的 target 缓存。"""
    global _cdp_ws
    if _cdp_target_cache is None:
        return False
    try:
        if _cdp_ws is not None:
            try:
                _cdp_ws.close()
            except Exception:
                pass
        cdp_connect(_cdp_target_cache)
        return True
    except Exception as e:
        print(f"[CDP] 重连失败：{e}")
        return False


def cdp_focus_game_canvas():
    """尽量把页面焦点放回游戏 canvas；切换快捷栏前尤其需要。"""
    result = cdp_evaluate(
        """
        (() => {
            const canvas = document.querySelector("canvas");
            if (canvas) {
                if (!canvas.hasAttribute("tabindex")) canvas.tabIndex = 0;
                canvas.focus();
                return {
                    ok: document.activeElement === canvas,
                    target: "canvas",
                };
            }
            window.focus();
            if (document.body && typeof document.body.focus === "function") {
                document.body.focus();
            }
            return {
                ok: document.activeElement === document.body,
                target: document.activeElement ? document.activeElement.tagName : "",
            };
        })()
        """,
        timeout=3.0,
    )
    return isinstance(result, dict) and bool(result.get("ok"))


def cdp_send_key(key_def, printable=False):
    """发按键。普通控制键走 rawKeyDown；数字快捷键走 printable 事件。"""
    base = {
        "windowsVirtualKeyCode": key_def["vk"],
        "nativeVirtualKeyCode": key_def["vk"],
        "code": key_def["code"],
        "key": key_def["key"],
    }

    def send(params):
        ok = _cdp_raw_send("Input.dispatchKeyEvent", params)
        if not ok and cdp_reconnect():
            ok = _cdp_raw_send("Input.dispatchKeyEvent", params)
        return ok

    down_params = dict(base, type="keyDown" if printable else "rawKeyDown")
    if printable:
        down_params["text"] = key_def["key"]
        down_params["unmodifiedText"] = key_def["key"]
    up_params = dict(base, type="keyUp")

    if not send(down_params):
        return False
    time.sleep(random_delay(0.03, 0.08))
    return send(up_params)


# ============================================================
# 空投/弹窗处理（与原版一致，全部通过 CDP 实现）
# ============================================================

def _airdrop_file_candidates(filename):
    base_dir = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / "signatures" / filename,
        base_dir / "signatures" / filename,
        Path.cwd() / filename,
        base_dir / filename,
        base_dir.parent / filename,
        base_dir.parent.parent / filename,
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([
            exe_dir / "signatures" / filename,
            exe_dir / filename,
            exe_dir.parent / filename,
            exe_dir.parent.parent / filename,
        ])
    return candidates


def _build_airdrop_signature(filename, html_marker_candidates, preferred_predicate):
    raw = ""
    for path in _airdrop_file_candidates(filename):
        try:
            raw = path.read_text(encoding="utf-8-sig").strip()
            if raw:
                break
        except OSError:
            continue

    if not raw:
        return None

    import html as html_mod
    visible_text = html_mod.unescape(re.sub(r"<[^>]+>", "\n", raw))
    text_markers = []
    for line in (part.strip() for part in visible_text.splitlines()):
        if len(line) >= 4 and line not in text_markers:
            text_markers.append(line)

    preferred_text_markers = [
        marker for marker in text_markers
        if preferred_predicate(marker)
    ]
    if len(preferred_text_markers) >= 2:
        text_markers = preferred_text_markers
    else:
        text_markers = text_markers[:6]

    html_markers = [
        marker for marker in html_marker_candidates
        if marker in raw
    ]

    return {
        "textMarkers": text_markers,
        "htmlMarkers": html_markers,
    }


def _load_airdrop_reward_signature():
    global _airdrop_reward_signature_cache
    if _airdrop_reward_signature_cache is not None:
        return _airdrop_reward_signature_cache

    _airdrop_reward_signature_cache = _build_airdrop_signature(
        AIR_DROP_REWARD_FILE,
        (
            "reward-title",
            "rewards-content",
            "hidden reward",
            "pizza-swap",
            "Claim",
        ),
        lambda marker: (
            "congrat" in marker.lower()
            or "hidden reward" in marker.lower()
            or "claim" == marker.lower()
            or "inswap" in marker.lower()
        ),
    )
    return _airdrop_reward_signature_cache


def _load_hidden_airdrop_signature():
    global _hidden_airdrop_signature_cache
    if _hidden_airdrop_signature_cache is not None:
        return _hidden_airdrop_signature_cache

    _hidden_airdrop_signature_cache = _build_airdrop_signature(
        HIDDEN_AIRDROP_FILE,
        (
            "Hidden Challenge",
            "Chop Master",
            "orderTree_step1",
            "orderTree_step2",
            "easterRule_step3",
            "Start!",
        ),
        lambda marker: (
            "hidden challenge" in marker.lower()
            or "chop master" in marker.lower()
            or "glowing trees" in marker.lower()
            or "start!" == marker.lower()
        ),
    )
    return _hidden_airdrop_signature_cache


def _load_no_energy_signature():
    global _no_energy_signature_cache
    if _no_energy_signature_cache is not None:
        return _no_energy_signature_cache

    _no_energy_signature_cache = _build_airdrop_signature(
        NO_ENERGY_FILE,
        (
            "energy deficiency",
            "Buy Energy",
            "Restore full in",
            "perform this action",
        ),
        lambda marker: (
            "energy deficiency" in marker.lower()
            or "enough energy" in marker.lower()
            or "buy energy" == marker.lower()
            or "restore full" in marker.lower()
        ),
    )
    return _no_energy_signature_cache


def _cdp_detect_airdrop_signature(signature):
    if not signature:
        return False

    script = r"""
(() => {
  const signature = %s;
  const body = document.body;
  if (!body) return { found: false, action: "no-body" };

  const textMarkers = signature.textMarkers || [];
  const htmlMarkers = signature.htmlMarkers || [];
  const bodyText = body.innerText || "";
  const bodyHtml = body.innerHTML || "";
  const textHits = textMarkers.filter((marker) => marker && bodyText.includes(marker)).length;
  const htmlHits = htmlMarkers.filter((marker) => marker && bodyHtml.includes(marker)).length;
  const requiredTextHits = Math.min(2, textMarkers.length);
  const requiredHtmlHits = Math.min(3, htmlMarkers.length);
  const foundByText = requiredTextHits > 0 && textHits >= requiredTextHits;
  const foundByHtml = requiredHtmlHits > 0 && htmlHits >= requiredHtmlHits;
  return { found: foundByText || foundByHtml };
})()
""" % json.dumps(signature, ensure_ascii=False)

    result = cdp_evaluate(script, timeout=AIR_DROP_CDP_TIMEOUT)
    return isinstance(result, dict) and bool(result.get("found"))


def cdp_handle_airdrop_reward():
    """检测并处理钓鱼奖励弹窗：找到最匹配的按钮并点击（Claim / Confirm 类按钮优先）。"""
    signature = _load_airdrop_reward_signature()
    if not _cdp_detect_airdrop_signature(signature):
        return False

    time.sleep(AIR_DROP_HANDLE_DELAY)

    handle_script = r"""
(() => {
  const signature = %s;
  const body = document.body;
  if (!body) return { found: false, action: "no-body" };

  const textMarkers = signature.textMarkers || [];
  const htmlMarkers = signature.htmlMarkers || [];
  const bodyText = body.innerText || "";
  const bodyHtml = body.innerHTML || "";
  const textHits = textMarkers.filter((marker) => marker && bodyText.includes(marker)).length;
  const htmlHits = htmlMarkers.filter((marker) => marker && bodyHtml.includes(marker)).length;
  const requiredTextHits = Math.min(2, textMarkers.length);
  const requiredHtmlHits = Math.min(3, htmlMarkers.length);
  const foundByText = requiredTextHits > 0 && textHits >= requiredTextHits;
  const foundByHtml = requiredHtmlHits > 0 && htmlHits >= requiredHtmlHits;
  if (!foundByText && !foundByHtml) return { found: false, action: "not-found" };

  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0
      && style.display !== "none"
      && style.visibility !== "hidden"
      && style.opacity !== "0";
  };

  const scoreNode = (el) => {
    const text = el.innerText || "";
    const html = el.innerHTML || "";
    const hits = textMarkers.filter((marker) => marker && text.includes(marker)).length
      + htmlMarkers.filter((marker) => marker && html.includes(marker)).length;
    const rect = el.getBoundingClientRect();
    return { el, hits, area: rect.width * rect.height };
  };

  const roots = Array.from(document.querySelectorAll("body *"))
    .filter(isVisible)
    .map(scoreNode)
    .filter((item) => item.hits >= Math.max(1, requiredTextHits))
    .sort((a, b) => b.hits - a.hits || a.area - b.area);
  const root = roots.length ? roots[0].el : body;

  const scopedButtons = root === body ? [] : Array.from(root.querySelectorAll("button,[role='button']"));
  const allButtons = Array.from(document.querySelectorAll("button,[role='button']"));
  const buttons = (scopedButtons.length ? scopedButtons : allButtons)
    .filter(isVisible)
    .sort((a, b) => {
      const aText = (a.innerText || "").trim().toLowerCase();
      const bText = (b.innerText || "").trim().toLowerCase();
      const aPrize = aText.includes("claim") || aText.includes("confirm");
      const bPrize = bText.includes("claim") || bText.includes("confirm");
      if (aPrize && !bPrize) return -1;
      if (!aPrize && bPrize) return 1;
      const aRect = a.getBoundingClientRect();
      const bRect = b.getBoundingClientRect();
      return (bRect.width * bRect.height) - (aRect.width * aRect.height);
    });

  if (!buttons.length) return { found: false, action: "no-button" };
  buttons[0].click();
  return { found: true, action: "clicked", buttonText: (buttons[0].innerText || "").trim() };
})()
""" % json.dumps(signature, ensure_ascii=False)

    result = cdp_evaluate(handle_script, timeout=3.0)
    if isinstance(result, dict) and result.get("found"):
        print(f"[弹窗] 已点击奖励按钮: {result.get('buttonText', '')}")
        return True
    return False


def cdp_detect_hidden_airdrop():
    """检测大空投任务弹窗，识别到则返回 True（由调用方暂停脚本）。"""
    signature = _load_hidden_airdrop_signature()
    return _cdp_detect_airdrop_signature(signature)


def cdp_handle_no_energy():
    """检测无体力弹窗，自动点击 Buy Energy 并返回 True。"""
    signature = _load_no_energy_signature()
    if not _cdp_detect_airdrop_signature(signature):
        return False

    time.sleep(AIR_DROP_HANDLE_DELAY)

    script = r"""
(() => {
  const signature = %s;
  const body = document.body;
  if (!body) return { found: false, action: "no-body" };

  const textMarkers = signature.textMarkers || [];
  const htmlMarkers = signature.htmlMarkers || [];
  const bodyText = body.innerText || "";
  const bodyHtml = body.innerHTML || "";
  const textHits = textMarkers.filter((marker) => marker && bodyText.includes(marker)).length;
  const htmlHits = htmlMarkers.filter((marker) => marker && bodyHtml.includes(marker)).length;
  const requiredTextHits = Math.min(2, textMarkers.length);
  const requiredHtmlHits = Math.min(3, htmlMarkers.length);
  if (!(requiredTextHits > 0 && textHits >= requiredTextHits) &&
      !(requiredHtmlHits > 0 && htmlHits >= requiredHtmlHits))
    return { found: false, action: "not-found" };

  const buyBtns = Array.from(document.querySelectorAll("button,[role='button']"))
    .filter((el) => {
      if (!el.offsetParent) return false;
      const text = (el.innerText || "").trim();
      return text.toLowerCase().includes("buy energy");
    });
  if (buyBtns.length) {
    buyBtns[0].click();
    return { found: true, action: "clicked-buy-energy" };
  }
  return { found: true, action: "no-buy-button" };
})()
""" % json.dumps(signature, ensure_ascii=False)

    result = cdp_evaluate(script, timeout=3.0)
    if isinstance(result, dict) and result.get("found"):
        print("[弹窗] 检测到无体力，已尝试点击 Buy Energy")
        return True
    return False


# ============================================================
# 鱼竿管理（通过 CDP 读 localStorage + API）
# ============================================================


# ============================================================
# 鱼竿 / 背包 API（与原版 fishing0.5.py 一致）
# ============================================================

def _normalize_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_tool_item(item):
    return {
        "userItemId": str(item.get("userItemId") or item.get("itemId") or ""),
        "singleType": str(item.get("singleType") or "").strip() or "Other",
        "name": str(item.get("name") or item.get("itemName") or "").strip(),
        "description": str(item.get("description") or "").strip(),
        "currentDurability": _normalize_int(item.get("currentDurability")),
        "maxDurability": _normalize_int(item.get("maxDurability")),
        "shortcut": str(item.get("shortcut") or "").strip(),
        "isNew": bool(item.get("isNew")),
    }


def _tool_item_sort_key(item):
    single_type = str(item.get("singleType") or "")
    shortcut = str(item.get("shortcut") or "").strip()
    shortcut_value = 99
    if shortcut.isdigit():
        shortcut_number = int(shortcut)
        if 1 <= shortcut_number <= 5:
            shortcut_value = shortcut_number

    display_name = str(item.get("description") or item.get("name") or "").lower()
    return (
        TOOL_SINGLE_TYPE_ORDER.get(single_type, len(TOOL_SINGLE_TYPE_ORDER)),
        shortcut_value,
        display_name,
        str(item.get("userItemId") or ""),
    )


def _extract_user_item_pack(api_payload):
    body = api_payload.get("body") if isinstance(api_payload, dict) else None
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return []
    pack = data.get("packResult")
    if not isinstance(pack, list):
        return []
    return [item for item in pack if isinstance(item, dict)]


def _extract_data_item_list(api_payload, key):
    body = api_payload.get("body") if isinstance(api_payload, dict) else None
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return []
    value = data.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _count_items_by_field(items, field, empty_label="empty"):
    counts = {}
    for item in items:
        value = str(item.get(field) or empty_label)
        counts[value] = counts.get(value, 0) + 1
    return counts


def _all_user_item_entries(api_payload):
    items = []
    for key in ("packResult", "equipmedResult", "waitPickResult"):
        items.extend(_extract_data_item_list(api_payload, key))
    return items


def _shortcut_fishing_poles(api_payload):
    slots = {}
    for item in _all_user_item_entries(api_payload):
        if str(item.get("singleType") or "") != "FishingPole":
            continue
        shortcut = str(item.get("shortcut") or "").strip()
        if not shortcut.isdigit():
            continue
        slot = int(shortcut)
        if 1 <= slot <= 5:
            slots[slot] = item
    return slots


def _tool_item_text(item):
    return " ".join(
        str(item.get(key) or "")
        for key in ("name", "itemName", "description", "tag", "type", "category", "subType", "singleType")
    ).lower()


def _is_tool_item(item):
    single_type = str(item.get("singleType") or "").strip()
    if single_type in TOOL_SINGLE_TYPE_ORDER:
        return True
    if single_type:
        return False
    if str(item.get("type") or "").strip().lower() != "equipment":
        return False
    return any(marker in _tool_item_text(item) for marker in TOOL_TEXT_MARKERS)


def _extract_tool_items(api_payload):
    tool_items = [_normalize_tool_item(item) for item in _extract_user_item_pack(api_payload) if _is_tool_item(item)]
    tool_items.sort(key=_tool_item_sort_key)
    return tool_items


def _extract_toolbar_slots(api_payload):
    slots = {}
    conflicts = []

    for item in _extract_tool_items(api_payload):
        shortcut = str(item.get("shortcut") or "").strip()
        if not shortcut.isdigit():
            continue
        slot = int(shortcut)
        if slot < 1 or slot > 5:
            continue
        if slot in slots:
            conflicts.append((slot, slots[slot], item))
            continue
        slots[slot] = item

    return slots, conflicts


async def _fetch_tool_items_via_work_api_async():
    assert ApiBrowserSession is not None
    assert ApiSatWorldClient is not None

    async with ApiBrowserSession(
        cdp_url=f"http://{CDP_HOST}:{CDP_PORT}",
        page_prefix="https://beta.satworld.io",
    ) as session:
        client = ApiSatWorldClient(session)
        return await client.get_user_items()


def _fetch_tool_items_via_work_api():
    if not _WORK_API_AVAILABLE:
        return None
    try:
        return asyncio.run(_fetch_tool_items_via_work_api_async())
    except Exception as e:
        return {
            "ok": False,
            "reason": "work_api_failed",
            "error": str(e),
        }


def _normalize_session_value(session):
    session = str(session or "")
    if session and "_" in session:
        base_session, suffix = session.rsplit("_", 1)
        if suffix.isdigit() and base_session:
            return base_session
    return session


def _extract_auth_candidates_from_storage(storage):
    if not isinstance(storage, dict):
        return []

    avatarversion = ""
    for key, value in storage.items():
        if "avatarversion" in str(key).lower() and value:
            avatarversion = str(value)
            break
    avatarversion = avatarversion or ""

    candidates = []
    seen = set()
    for key, value in storage.items():
        key_str = str(key)
        if not key_str.endswith("_session") or not value:
            continue
        address = key_str[: -len("_session")]
        session = _normalize_session_value(value)
        if not address or not session or address in seen:
            continue
        seen.add(address)
        candidates.append({
            "address": address,
            "session": session,
            "avatarversion": avatarversion,
        })
    return candidates


def _auth_address(auth):
    return str((auth or {}).get("address") or "").strip().lower()


def _mask_address_tail(address, tail_len=5):
    text = str(address or "").strip()
    if not text:
        return "unknown"
    if len(text) <= tail_len:
        return text
    return f"...{text[-tail_len:]}"


def _active_addresses_from_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return []
    addresses = []
    for url in snapshot.get("apiResources") or []:
        for match in re.findall(r"bc1p[a-z0-9]{20,}", str(url).lower()):
            if match not in addresses:
                addresses.append(match)
    return addresses


def _choose_auth_candidate(auth_candidates):
    global SELECTED_AUTH_ADDRESS

    if not auth_candidates:
        return None

    selected = str(SELECTED_AUTH_ADDRESS or "").strip().lower()
    for auth in auth_candidates:
        if selected and _auth_address(auth) == selected:
            return auth

    if len(auth_candidates) == 1:
        SELECTED_AUTH_ADDRESS = _auth_address(auth_candidates[0])
        return auth_candidates[0]

    print("[钱包] 检测到多个钱包 session，请选择当前游戏钱包：")
    for index, auth in enumerate(auth_candidates):
        address = _auth_address(auth)
        print(f"  [{index}] {_mask_address_tail(address)}")

    while not should_exit:
        try:
            choice = input("钱包编号 > ").strip()
        except EOFError:
            print("[钱包] 无法读取控制台输入")
            return None
        if not choice and len(auth_candidates) == 1:
            SELECTED_AUTH_ADDRESS = _auth_address(auth_candidates[0])
            return auth_candidates[0]
        try:
            index = int(choice)
        except ValueError:
            print("[钱包] 请输入列表中的编号")
            continue
        if 0 <= index < len(auth_candidates):
            SELECTED_AUTH_ADDRESS = _auth_address(auth_candidates[index])
            print(f"[钱包] 已选择 {_mask_address_tail(SELECTED_AUTH_ADDRESS)}")
            return auth_candidates[index]
        print("[钱包] 编号无效")
    return None


def _fetch_tool_items_via_http(auth, timeout=8.0):
    headers = {
        "address": auth["address"],
        "session": auth["session"],
        "avatarversion": auth.get("avatarversion", ""),
        "origin": "https://beta.satworld.io",
        "referer": "https://beta.satworld.io/",
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36"
        ),
    }

    request = urllib.request.Request(API_USER_ITEM_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode("utf-8", errors="replace")
        except Exception:
            text = ""
        body = {"raw": text}
        try:
            if text:
                body = json.loads(text)
        except Exception:
            pass
        return {
            "ok": False,
            "status": e.code,
            "body": body,
            "reason": "http_error",
        }
    except Exception as e:
        return {
            "ok": False,
            "reason": "http_request_failed",
            "error": str(e),
        }

    try:
        body = json.loads(text)
    except Exception:
        body = {"raw": text}

    return {
        "ok": 200 <= int(status) < 300,
        "status": int(status),
        "body": body,
    }


def _storage_context_snapshot():
    return cdp_evaluate(
        """
        (() => {
            const maskValue = (key, value) => {
                const text = String(value || "");
                const loweredKey = String(key || "").toLowerCase();
                const sensitive = loweredKey.includes("session")
                    || loweredKey.includes("token")
                    || loweredKey.includes("auth")
                    || loweredKey.includes("address");
                if (!sensitive && text.length <= 160) return text;
                if (text.length <= 12) return text;
                return `${text.slice(0, 6)}...${text.slice(-6)}`;
            };
            const collect = (storage, kind) => {
                const rows = [];
                for (let i = 0; i < storage.length; i += 1) {
                    const key = storage.key(i);
                    const value = storage.getItem(key) || "";
                    rows.push({
                        kind,
                        key,
                        valueLength: value.length,
                        preview: maskValue(key, value),
                    });
                }
                return rows;
            };
            const apiResources = performance.getEntriesByType("resource")
                .map((entry) => String(entry.name || ""))
                .filter((name) => name.includes("api.satworld.io") || name.includes("/game/"))
                .slice(-80);
            return {
                storage: [
                    ...collect(window.localStorage, "localStorage"),
                    ...collect(window.sessionStorage, "sessionStorage"),
                ].slice(0, 120),
                apiResources,
            };
        })()
        """,
        timeout=5.0,
    )


def _payload_pack_len(payload):
    return len(_extract_user_item_pack(payload)) if isinstance(payload, dict) else 0


def fetch_tool_items_via_cdp():
    work_payload = _fetch_tool_items_via_work_api()
    if isinstance(work_payload, dict) and work_payload.get("ok"):
        return work_payload

    storage = cdp_get_local_storage_items()
    auth_candidates = _extract_auth_candidates_from_storage(storage)
    auth_candidates.sort(
        key=lambda auth: str(auth.get("address") or ""),
    )

    if auth_candidates:
        auth = _choose_auth_candidate(auth_candidates)
        if auth is None:
            return {"ok": False, "reason": "auth_selection_cancelled"}
        http_payload = _fetch_tool_items_via_http(auth)
        if isinstance(http_payload, dict) and http_payload.get("ok"):
            return http_payload
        if isinstance(work_payload, dict):
            return work_payload
        return http_payload
    if isinstance(work_payload, dict):
        return work_payload
    return {
        "ok": False,
        "reason": "missing_auth",
        "storage_keys": list(storage.keys())[:20],
    }


def _rod_status_text(slots):
    parts = []
    for slot in range(1, 6):
        item = slots.get(slot)
        if not item:
            continue
        parts.append(f"{slot}:{_normalize_int(item.get('currentDurability'))}/{_normalize_int(item.get('maxDurability'))}")
    return " ".join(parts) if parts else "none"


def _rod_durability_snapshot(slots):
    return {
        slot: _normalize_int(item.get("currentDurability"))
        for slot, item in slots.items()
    }


def _infer_used_rod_slot(previous, current):
    if not isinstance(previous, dict):
        return None
    changed = []
    for slot, before in previous.items():
        after = current.get(slot, -1)
        if after < before:
            changed.append((slot, before - after))
    if not changed:
        return None
    return max(changed, key=lambda item: item[1])[0]


def _ordered_available_rod_slots(slots, start_after=None):
    ordered = list(range(1, 6))
    if start_after in ordered:
        index = ordered.index(start_after)
        ordered = ordered[index + 1:] + ordered[:index + 1]
    return [
        slot for slot in ordered
        if slot in slots and _normalize_int(slots[slot].get("currentDurability")) > 0
    ]


def _switch_to_rod_slot(slot, reason="", force=False):
    global CURRENT_ROD_SLOT
    if slot not in KEY_DIGITS:
        return False
    if CURRENT_ROD_SLOT == slot and not force:
        return True

    time.sleep(gaussian_delay(*ROD_SWITCH_PRE_KEY_DELAY))
    cdp_focus_game_canvas()
    for press_index in range(ROD_SWITCH_KEY_PRESSES):
        if not cdp_send_key(KEY_DIGITS[slot], printable=True):
            print(f"[鱼竿] 切换到快捷栏 {slot} 失败")
            return False
        if press_index + 1 < ROD_SWITCH_KEY_PRESSES:
            time.sleep(gaussian_delay(*ROD_SWITCH_KEY_INTERVAL))

    CURRENT_ROD_SLOT = slot
    suffix = f"（{reason}）" if reason else ""
    print(f"[鱼竿] 已发送快捷栏 {slot} 切换按键{suffix}")
    time.sleep(random_delay(ROD_SWITCH_SETTLE_DELAY, ROD_SWITCH_SETTLE_DELAY + 0.15))
    return True


def _pause_no_usable_rod(snapshot):
    global running, paused, CURRENT_ROD_SLOT, LAST_ROD_SLOTS, ROD_EXPECTED_DURABILITY

    print("[鱼竿] 快捷栏 1-5 没有可用鱼竿，自动暂停")
    running = False
    paused = True
    CURRENT_ROD_SLOT = None
    ROD_EXPECTED_DURABILITY = None
    LAST_ROD_SLOTS = snapshot
    play_sound_async()
    return False


def ensure_usable_rod(reason="", force_switch=False):
    """确保当前选中了一个有耐久的鱼竿（通过游戏 API 查询）"""
    global CURRENT_ROD_SLOT, LAST_ROD_SLOTS, ROD_EXPECTED_DURABILITY

    api_payload = fetch_tool_items_via_cdp()
    if not isinstance(api_payload, dict) or not api_payload.get("ok"):
        detail = api_payload.get("reason") or api_payload.get("status") or api_payload.get("error") or "unknown"
        print(f"[鱼竿] 读取 /game/user-item 失败：{detail}")
        return False

    slots = _shortcut_fishing_poles(api_payload)
    snapshot = _rod_durability_snapshot(slots)
    print(f"[鱼竿] 快捷栏耐久 {_rod_status_text(slots)}")

    if CURRENT_ROD_SLOT is None:
        available = _ordered_available_rod_slots(slots)
        if available:
            slot = available[0]
            switched = _switch_to_rod_slot(slot, reason=reason or "初始化鱼竿", force=True)
            if switched:
                ROD_EXPECTED_DURABILITY = _normalize_int(slots[slot].get("currentDurability"))
                print(f"[鱼竿] 记录当前快捷栏 {slot}，预计剩余耐久 {ROD_EXPECTED_DURABILITY}")
            LAST_ROD_SLOTS = snapshot
            return switched
        return _pause_no_usable_rod(snapshot)

    current_item = slots.get(CURRENT_ROD_SLOT)
    current_durability = _normalize_int(current_item.get("currentDurability")) if current_item else 0
    if current_durability > 0:
        ROD_EXPECTED_DURABILITY = current_durability
        if force_switch:
            switched = _switch_to_rod_slot(CURRENT_ROD_SLOT, reason=reason or "重新确认鱼竿", force=True)
            if not switched:
                ROD_EXPECTED_DURABILITY = None
            LAST_ROD_SLOTS = snapshot
            return switched
        print(f"[鱼竿] 更新当前快捷栏 {CURRENT_ROD_SLOT}，预计剩余耐久 {ROD_EXPECTED_DURABILITY}")
        LAST_ROD_SLOTS = snapshot
        return True

    available = _ordered_available_rod_slots(slots, start_after=CURRENT_ROD_SLOT)
    if not available:
        return _pause_no_usable_rod(snapshot)

    slot = available[0]
    switched = _switch_to_rod_slot(slot, reason=reason or "选择可用鱼竿", force=True)
    if switched:
        ROD_EXPECTED_DURABILITY = _normalize_int(slots[slot].get("currentDurability"))
        print(f"[鱼竿] 记录当前快捷栏 {slot}，预计剩余耐久 {ROD_EXPECTED_DURABILITY}")
    LAST_ROD_SLOTS = snapshot
    return switched


def record_successful_reel(defer_zero_switch=False):
    """收竿成功后扣减耐久计数"""
    global ROD_EXPECTED_DURABILITY

    if ROD_EXPECTED_DURABILITY is None:
        if defer_zero_switch:
            return True
        return ensure_usable_rod("收杆后校准")

    ROD_EXPECTED_DURABILITY = max(ROD_EXPECTED_DURABILITY - 1, 0)
    suffix = f"{CURRENT_ROD_SLOT}:{ROD_EXPECTED_DURABILITY}" if CURRENT_ROD_SLOT is not None else str(ROD_EXPECTED_DURABILITY)
    print(f"[鱼竿] 计数耐久 {suffix}")

    if ROD_EXPECTED_DURABILITY <= 0:
        if defer_zero_switch:
            return True
        print("[鱼竿] 等待杆子消失动画...")
        time.sleep(1.0)
        return ensure_usable_rod("耐久计数归零校准")
    return True


def pause_for_no_energy():
    """无体力时暂停"""
    global paused
    paused = True
    play_sound_async()
    print("[暂停] 体力不足，请手动处理")


def pause_for_hidden_airdrop():
    """大空投任务时暂停"""
    global paused
    paused = True
    play_sound_async()
    print("[暂停] 检测到大空投任务，请手动处理")


# ============================================================
# 装备制作（与原版一致）
# ============================================================

async def cdp_send_async(method, params=None):
    """异步CDP发送函数,用于装备制作模块"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _cdp_call, method, params)
    return result


async def send_key_async(key_def):
    """异步发送按键函数,用于装备制作模块"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, cdp_send_key, key_def)
    return result


def init_crafting_manager():
    """初始化装备制作管理器"""
    global crafting_manager
    if not _CRAFTING_AVAILABLE:
        print("[制作] 装备制作模块不可用")
        return False
    crafting_manager = CraftingManager(cdp_send_async, send_key_async)
    print("[制作] 装备制作管理器已初始化")
    return True


def start_crafting_with_input():
    """启动装备制作流程(带用户输入)"""
    global crafting_task, paused, running

    if not _CRAFTING_AVAILABLE or crafting_manager is None:
        print("[制作] 装备制作功能不可用")
        return

    if running:
        paused = True
        print("[制作] 已暂停钓鱼")

    try:
        count_str = input("[制作] 请输入要制作的数量: ")
        count = int(count_str)
        if count <= 0:
            print("[制作] 数量必须大于0")
            return

        print(f"[制作] 开始制作 {count} 个装备...")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        crafting_task = loop.create_task(crafting_manager.start_crafting(count))
        loop.run_until_complete(crafting_task)
        loop.close()

        print("[制作] 制作流程已完成")

    except ValueError:
        print("[制作] 输入无效,请输入数字")
    except KeyboardInterrupt:
        print("[制作] 制作已取消")
        if crafting_manager:
            crafting_manager.stop_crafting()
    except Exception as e:
        print(f"[制作] 发生错误: {e}")


def stop_crafting():
    global crafting_task
    if crafting_manager:
        crafting_manager.stop_crafting()
    crafting_task = None
    print("[装备] 制作任务已停止")
# ============================================================
# 图像识别：鱼漂检测（与原版一致，纯 OpenCV）
# ============================================================

def find_float_target(frame, red_lower, red_upper, red_lower2=None, red_upper2=None):
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    red_mask = cv2.inRange(hsv, red_lower, red_upper)
    if red_lower2 is not None and red_upper2 is not None:
        red_mask2 = cv2.inRange(hsv, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask, red_mask2)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    candidates = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < FLOAT_MIN_AREA:
            continue
        candidates.append((area, c))

    if not candidates:
        return None

    area, contour = max(candidates, key=lambda x: x[0])
    m = cv2.moments(contour)
    if m["m00"] == 0:
        return None
    center = int(m["m10"] / m["m00"]), int(m["m01"] / m["m00"])
    x, y, w, h = cv2.boundingRect(contour)
    side = max(w, h) + FLOAT_BOX_PADDING * 2
    side = clamp(side, FLOAT_BOX_MIN_SIZE, FLOAT_BOX_MAX_SIZE)
    box = _square_box_from_center(center, side, frame.shape[1], frame.shape[0])
    confirm_box = _expand_box(box, FLOAT_CONFIRM_BOX_PADDING, frame.shape[1], frame.shape[0])
    return {
        "center": center,
        "box": box,
        "confirm_box": confirm_box,
        "red_bbox": (x, y, x + w, y + h),
        "area": area,
    }


def find_float_center(frame, red_lower, red_upper):
    target = find_float_target(frame, red_lower, red_upper)
    return target["center"] if target is not None else None


def build_shadow_mask(roi, float_center_local, track_radius, red_lower, red_upper, red_lower2=None, red_upper2=None):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    local_median = int(np.median(blurred))
    threshold = max(0, local_median - FISH_BRIGHTNESS_DROP)
    dark = cv2.inRange(blurred, 0, threshold)

    red_mask = cv2.inRange(roi, red_lower, red_upper)
    if red_lower2 is not None and red_upper2 is not None:
        red_mask2 = cv2.inRange(roi, red_lower2, red_upper2)
        red_mask = cv2.bitwise_or(red_mask, red_mask2)
    dark = cv2.bitwise_and(dark, cv2.bitwise_not(red_mask))

    ring = np.zeros_like(dark)
    cv2.circle(ring, float_center_local, track_radius, 255, -1)
    dark = cv2.bitwise_and(dark, ring)

    kernel = np.ones((3, 3), np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel)
    return dark, threshold


def contour_overlaps_bite_pair(contour, mask_shape, trigger_box_local, confirm_box_local):
    trigger = np.zeros(mask_shape, dtype=np.uint8)
    confirm = np.zeros(mask_shape, dtype=np.uint8)
    cmask = np.zeros(mask_shape, dtype=np.uint8)
    _draw_box_border(trigger, trigger_box_local, 255, FLOAT_BOX_TRIGGER_THICKNESS)
    _draw_box_border(confirm, confirm_box_local, 255, FLOAT_CONFIRM_BOX_THICKNESS)
    cv2.drawContours(cmask, [contour], -1, 255, -1)
    hits_trigger = cv2.countNonZero(cv2.bitwise_and(trigger, cmask)) > 0
    hits_confirm = cv2.countNonZero(cv2.bitwise_and(confirm, cmask)) > 0
    return hits_trigger and hits_confirm


def find_fish_shadow(frame, float_target, red_lower, red_upper, red_lower2=None, red_upper2=None):
    if float_target is None:
        return None
    float_center = float_target["center"]
    cx, cy = float_center
    left = max(cx - FISH_TRACK_RADIUS, 0)
    top = max(cy - FISH_TRACK_RADIUS, 0)
    right = min(cx + FISH_TRACK_RADIUS + 1, frame.shape[1])
    bottom = min(cy + FISH_TRACK_RADIUS + 1, frame.shape[0])
    roi = frame[top:bottom, left:right]
    if roi.size == 0:
        return None

    local = (cx - left, cy - top)
    track_r = min(FISH_TRACK_RADIUS, local[0], local[1],
                  roi.shape[1] - local[0] - 1, roi.shape[0] - local[1] - 1)
    if track_r <= FLOAT_BOX_TRIGGER_THICKNESS:
        return None

    trigger_box_local = _offset_box(float_target["box"], left, top, roi.shape[1], roi.shape[0])
    confirm_box_local = _offset_box(float_target["confirm_box"], left, top, roi.shape[1], roi.shape[0])
    mask, threshold = build_shadow_mask(roi, local, track_r, red_lower, red_upper, red_lower2, red_upper2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    bite = []
    for c in contours:
        area = cv2.contourArea(c)
        if area < FISH_MIN_AREA:
            continue
        hit = contour_overlaps_bite_pair(c, mask.shape, trigger_box_local, confirm_box_local)
        item = {"contour_local": c, "area": area, "bite_triggered": hit}
        candidates.append(item)
        if hit:
            bite.append(item)

    if not candidates:
        return None

    sel = max(bite, key=lambda i: i["area"]) if bite else max(candidates, key=lambda i: i["area"])
    c_frame = sel["contour_local"] + np.array([[[left, top]]])
    x, y, w, h = cv2.boundingRect(c_frame)
    return {
        "bbox": (x, y, w, h),
        "contour": c_frame,
        "area": sel["area"],
        "bite_triggered": sel["bite_triggered"],
        "brightness_threshold": threshold,
        "float_box": float_target["box"],
        "confirm_box": float_target["confirm_box"],
    }


def fish_touching_float(fs):
    return fs is not None and fs["bite_triggered"]


# ============================================================
# 预览窗口（与原版一致，OpenCV 跨平台）
# ============================================================

def pin_preview_window():
    """macOS: 尝试置顶预览窗口"""
    global preview_window_pinned
    if preview_window_pinned:
        return
    try:
        # macOS 没有直接的窗口置顶 API，但可以用 cv2 属性
        cv2.setWindowProperty(PREVIEW_WINDOW_NAME, cv2.WND_PROP_TOPMOST, 1)
        preview_window_pinned = True
    except Exception:
        pass


def _draw_placeholder(msg):
    img = np.zeros((300, 600, 3), dtype=np.uint8)
    cv2.putText(img, msg, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imshow(PREVIEW_WINDOW_NAME, img)
    pin_preview_window()
    cv2.waitKey(1)


def _check_preview_window():
    global should_exit
    try:
        if cv2.getWindowProperty(PREVIEW_WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            should_exit = True
    except Exception:
        should_exit = True


def mouse_callback(event, x, y, flags, param):
    global dragging, drag_start_x, drag_start_y, temp_region
    scale = param.get("scale", 1.0) if param else 1.0
    rx = int(x / scale)
    ry = int(y / scale)

    if event == cv2.EVENT_LBUTTONDOWN:
        dragging = True
        drag_start_x, drag_start_y = rx, ry
        temp_region = None
    elif event == cv2.EVENT_MOUSEMOVE:
        if dragging:
            x1, y1 = min(drag_start_x, rx), min(drag_start_y, ry)
            w, h = abs(rx - drag_start_x), abs(ry - drag_start_y)
            temp_region = {"x": x1, "y": y1, "width": w, "height": h}
    elif event == cv2.EVENT_LBUTTONUP:
        dragging = False
        if temp_region and temp_region["width"] > 5 and temp_region["height"] > 5:
            CAPTURE_REGION["x"] = temp_region["x"]
            CAPTURE_REGION["y"] = temp_region["y"]
            CAPTURE_REGION["width"] = temp_region["width"]
            CAPTURE_REGION["height"] = temp_region["height"]
            print(f"[选区] x={CAPTURE_REGION['x']}, y={CAPTURE_REGION['y']}, "
                  f"w={CAPTURE_REGION['width']}, h={CAPTURE_REGION['height']}")
        temp_region = None


def show_selection_preview():
    if not is_window_ready(TARGET_WINDOW_ID):
        _draw_placeholder("Target window not ready")
        _check_preview_window()
        return

    frame, cw, ch = capture_window_client(TARGET_WINDOW_INFO)
    if frame is None:
        _draw_placeholder("Capture failed - check screen recording permission")
        _check_preview_window()
        return

    clamp_region_to_client(cw, ch)
    preview = frame.copy()

    rx, ry = CAPTURE_REGION["x"], CAPTURE_REGION["y"]
    rw, rh = CAPTURE_REGION["width"], CAPTURE_REGION["height"]
    cv2.rectangle(preview, (rx, ry), (rx + rw, ry + rh), (0, 255, 0), 2)

    if temp_region:
        cv2.rectangle(preview,
                      (temp_region["x"], temp_region["y"]),
                      (temp_region["x"] + temp_region["width"],
                       temp_region["y"] + temp_region["height"]),
                      (255, 0, 0), 2)

    cv2.putText(preview, "Drag to select | F7:start | ESC:stop",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    btn_x, btn_y = preview.shape[1] - 120, 10
    cv2.rectangle(preview, (btn_x, btn_y), (btn_x + 110, btn_y + 40), (0, 0, 255), -1)
    cv2.putText(preview, "QUIT (Q)", (btn_x + 10, btn_y + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

    scale = 0.5 if preview.shape[1] > 1200 else 1.0
    disp = preview if scale == 1.0 else cv2.resize(
        preview, (int(preview.shape[1] * scale), int(preview.shape[0] * scale)),
        interpolation=cv2.INTER_AREA)

    MOUSE_PARAM["scale"] = scale
    MOUSE_PARAM["client_w"] = cw
    MOUSE_PARAM["client_h"] = ch

    cv2.imshow(PREVIEW_WINDOW_NAME, disp)
    pin_preview_window()
    _check_preview_window()
    cv2.waitKey(1)


def build_status_text(float_target, fs):
    if float_target is None:
        return "FLOAT: missing | FISH: missing"
    if fs is None:
        return "FLOAT: tracked | FISH: missing"
    if fs["bite_triggered"]:
        return f"FLOAT: tracked | BITE: triggered area={int(fs['area'])}"
    return f"FLOAT: tracked | FISH: tracked area={int(fs['area'])}"


def show_fishing_preview(frame, float_target, fs):
    preview = frame.copy()
    if float_target is not None:
        cx, cy = float_target["center"]
        cv2.circle(preview, (cx, cy), FISH_TRACK_RADIUS, (0, 255, 255), 1)
        _draw_box_border(preview, float_target["confirm_box"], (0, 165, 255), 2)
        _draw_box_border(preview, float_target["box"], (0, 0, 0), 2)

    if fs is not None:
        color = (0, 255, 0) if fs["bite_triggered"] else (0, 255, 255)
        cv2.drawContours(preview, [fs["contour"]], -1, color, 2)
        x, y, w, h = fs["bbox"]
        cv2.rectangle(preview, (x, y), (x + w, y + h), color, 1)

    status = "[PAUSED]" if paused else "[RUNNING]"
    cv2.putText(preview, f"{status} F7:pause | ESC:stop",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    cv2.putText(preview, build_status_text(float_target, fs),
                (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)

    btn_x, btn_y = preview.shape[1] - 120, 10
    cv2.rectangle(preview, (btn_x, btn_y), (btn_x + 40, btn_y + 40), (0, 0, 255), -1)
    cv2.putText(preview, "QUIT", (btn_x + 5, btn_y + 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imshow(PREVIEW_WINDOW_NAME, preview)
    pin_preview_window()
    _check_preview_window()
    cv2.waitKey(1)


def refresh_fishing_preview(red_lower, red_upper, red_lower2=None, red_upper2=None):
    frame_full, cw, ch = capture_window_client(TARGET_WINDOW_INFO)
    if frame_full is None:
        return None, None, None
    clamp_region_to_client(cw, ch)
    x, y, w, h = CAPTURE_REGION["x"], CAPTURE_REGION["y"], CAPTURE_REGION["width"], CAPTURE_REGION["height"]
    frame = frame_full[y:y + h, x:x + w]
    if frame.size == 0:
        return None, None, None
    ft = find_float_target(frame, red_lower, red_upper, red_lower2, red_upper2)
    fs = find_fish_shadow(frame, ft, red_lower, red_upper, red_lower2, red_upper2)
    show_fishing_preview(frame, ft, fs)
    return frame, ft, fs


def wait_with_preview(duration, red_lower, red_upper, red_lower2=None, red_upper2=None):
    end = time.time() + duration
    while time.time() < end:
        if should_exit or paused or not running:
            return False
        if is_window_minimized(TARGET_WINDOW_INFO):
            return False
        refresh_fishing_preview(red_lower, red_upper, red_lower2, red_upper2)
        remaining = end - time.time()
        time.sleep(min(0.05, max(remaining, 0)))
    return True


# ============================================================
# 键盘监听（pynput，跨平台）
# ============================================================

def on_press(key):
    global running, paused, should_exit, preview_window_pinned
    global TARGET_WINDOW_ID, TARGET_WINDOW_INFO

    try:
        if key == keyboard.Key.f8:
            # 列出所有浏览器窗口，F8 循环切换绑定
            windows = list_browser_windows()
            if not windows:
                print("\n[F8] 未检测到浏览器窗口")
            elif len(windows) == 1:
                wid, name, winfo = windows[0]
                TARGET_WINDOW_ID = wid
                TARGET_WINDOW_INFO = winfo
                print(f"\n[F8] 已绑定窗口: {name[:80]}")
                play_sound_async()
            else:
                # 多个窗口：首次 F8 绑定第一个，再按 F8 循环到下一个
                current_idx = 0
                for i, (wid, _, _) in enumerate(windows):
                    if wid == TARGET_WINDOW_ID:
                        current_idx = i
                        break
                next_idx = (current_idx + 1) % len(windows) if TARGET_WINDOW_ID else 0
                wid, name, winfo = windows[next_idx]
                TARGET_WINDOW_ID = wid
                TARGET_WINDOW_INFO = winfo
                print(f"\n[F8] 窗口 [{next_idx}/{len(windows)-1}]: {name[:80]}")
                for i, (w, n, _) in enumerate(windows):
                    marker = " <--" if w == wid else ""
                    print(f"  [{i}] {n[:80]}{marker}")
                play_sound_async()
        elif key == keyboard.Key.f7:
            if TARGET_WINDOW_ID is None:
                print("\n[F7] 请先按 F8 绑定浏览器窗口")
            elif running and not paused:
                paused = True
                print("\n[F7] 已暂停")
            elif running and paused:
                paused = False
                print("\n[F7] 已恢复")
            else:
                running = True
                paused = False
                print("\n[F7] 开始钓鱼")
                play_sound_async()
        elif key == keyboard.Key.f9:
            preview_window_pinned = not preview_window_pinned
            try:
                cv2.setWindowProperty(PREVIEW_WINDOW_NAME, cv2.WND_PROP_TOPMOST,
                                      1 if preview_window_pinned else 0)
            except Exception:
                pass
            print(f"\n[F9] 预览窗口置顶: {preview_window_pinned}")
        elif key == keyboard.Key.f1:
            if _CRAFTING_AVAILABLE and crafting_manager:
                print("\n[F1] 启动装备制作...")
                # 装备制作需要在主线程中运行 asyncio 事件循环
                threading.Thread(target=start_crafting_with_input, daemon=True).start()
        elif key == keyboard.Key.f2:
            # F2: 保存调试截图，用于诊断颜色阈值问题
            threading.Thread(target=save_debug_screenshot, daemon=True).start()
        elif key == keyboard.Key.esc:
            print("\n[Esc] 正在退出...")
            should_exit = True
            running = False
    except Exception as e:
        print(f"[按键] 处理异常: {e}")


listener = keyboard.Listener(on_press=on_press)
listener.start()


# ============================================================
# 主循环（与原版逻辑一致）
# ============================================================

def main():
    global should_exit, _cdp_target_cache, PREVIEW_WINDOW_NAME
    global TARGET_WINDOW_ID, TARGET_WINDOW_INFO

    print("=== 自动钓鱼脚本 0.5（macOS CDP 注入版）===")
    print(f"CDP 端口: {CDP_HOST}:{CDP_PORT}")
    print("快捷键: F7 启动/暂停钓鱼")
    print("快捷键: F1 装备制作")
    print()
    print("先决条件：")
    print(f"  运行 start.sh 启动带调试端口的 Chrome")
    print(f"  Chrome 启动参数 --remote-debugging-port={CDP_PORT}")
    print("  pip3 install websocket-client opencv-python numpy pynput mss")
    print("  pip3 install pyobjc-framework-Quartz")
    print()
    print("macOS 特别说明：")
    print("  首次运行需要授予「屏幕录制」权限：")
    print("  系统设置 → 隐私与安全性 → 屏幕录制 → 允许 Terminal")
    print()
    print("操作：F8 绑定窗口 → 选 tab → 拖框选区 → F7 启动/暂停 → ESC 停止/退出")
    print("提示：浏览器窗口需要保持在屏幕上（不可最小化）")
    print()

    pick_target_window()
    if should_exit or TARGET_WINDOW_ID is None:
        return

    target = cdp_pick_target(
        window_title_hint=get_window_title(TARGET_WINDOW_INFO),
        host=CDP_HOST, port=CDP_PORT
    )
    if target is None:
        print("[终止] 未能获取 CDP target")
        return
    _cdp_target_cache = target
    try:
        cdp_connect(target)
    except Exception as e:
        print(f"[终止] CDP 连接失败：{e}")
        return

    # 初始化装备制作管理器
    if _CRAFTING_AVAILABLE:
        init_crafting_manager()

    red_lower = np.array([0, 60, 100])
    red_upper = np.array([30, 255, 255])
    # macOS 颜色渲染与 Windows 不同，额外覆盖深红范围
    red_lower2 = np.array([170, 60, 100])
    red_upper2 = np.array([180, 255, 255])

    cv2.namedWindow(PREVIEW_WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(PREVIEW_WINDOW_NAME, mouse_callback, MOUSE_PARAM)

    while not should_exit:
        if not is_window_ready(TARGET_WINDOW_ID):
            print("[错误] 目标窗口已关闭")
            break

        if is_window_minimized(TARGET_WINDOW_INFO):
            _draw_placeholder("Target minimized - waiting...")
            _check_preview_window()
            time.sleep(0.5)
            continue

        if not running:
            show_selection_preview()
            time.sleep(0.05)
            continue

        if paused:
            refresh_fishing_preview(red_lower, red_upper, red_lower2, red_upper2)
            time.sleep(0.05)
            continue

        if CURRENT_ROD_SLOT is None or ROD_EXPECTED_DURABILITY is None or ROD_EXPECTED_DURABILITY <= 0:
            if not ensure_usable_rod("启动检查"):
                time.sleep(0.5)
                continue

        if ROD_EXPECTED_DURABILITY is None or ROD_EXPECTED_DURABILITY <= 0:
            time.sleep(0.5)
            continue

        print("[动作] 抛竿")
        if not cdp_send_key(KEY_F):
            print("[动作] 抛竿失败")
            time.sleep(0.5)
            continue
        if cdp_handle_no_energy():
            pause_for_no_energy()
            continue

        bite = False
        start = time.time()
        detect_after = start + CAST_BITE_DETECTION_DELAY
        timeout = random_delay(23, 27)
        while running and not paused and not bite and not should_exit:
            if time.time() - start > timeout:
                print("[提示] 等待超时，重抛")
                ensure_usable_rod("等待超时校准", force_switch=True)
                break
            if is_window_minimized(TARGET_WINDOW_INFO):
                break
            _, _, fs = refresh_fishing_preview(red_lower, red_upper, red_lower2, red_upper2)
            if time.time() < detect_after:
                time.sleep(random_delay(0.04, 0.08))
                continue
            if fish_touching_float(fs):
                r_delay = gaussian_delay(0.13, 0.17)
                print(f"[检测] 咬钩！反应 {r_delay:.2f}s")
                bite = True
                if not wait_with_preview(r_delay, red_lower, red_upper, red_lower2, red_upper2):
                    bite = False
                break
            time.sleep(random_delay(0.04, 0.08))

        if bite and running and not paused and not should_exit:
            if not cdp_send_key(KEY_F):
                print("[动作] 收竿失败")
                time.sleep(0.5)
                continue
            reel_delay = random_delay(6.0, 7.0)
            print(f"[动作] 收竿（等待 {reel_delay:.2f}s）")
            if wait_with_preview(reel_delay, red_lower, red_upper, red_lower2, red_upper2):
                if cdp_handle_no_energy():
                    pause_for_no_energy()
                    continue
                if cdp_detect_hidden_airdrop():
                    record_successful_reel(defer_zero_switch=True)
                    pause_for_hidden_airdrop()
                    continue
                cdp_handle_airdrop_reward()
                record_successful_reel()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序已退出")
    finally:
        listener.stop()
        try:
            if _cdp_ws is not None:
                _cdp_ws.close()
        except Exception:
            pass
        cv2.destroyAllWindows()
