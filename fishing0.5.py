import ctypes
import ctypes.wintypes as wt
import asyncio
import json
from pathlib import Path
import re
import sys
import threading
import time
import random
import urllib.error
import urllib.parse
import urllib.request
import winsound
import argparse

import cv2
import numpy as np
from pynput import keyboard

try:
    import websocket  # pip install websocket-client
    _WEBSOCKET_AVAILABLE = True
except ImportError:
    websocket = None
    _WEBSOCKET_AVAILABLE = False

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


# ---------- DPI 感知 ----------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------- 常量 ----------
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

PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0
BI_RGB = 0

# F 键的 CDP 描述
KEY_F = {"vk": 0x46, "code": "KeyF", "key": "f"}
KEY_DIGITS = {
    slot: {"vk": 0x30 + slot, "code": f"Digit{slot}", "key": str(slot)}
    for slot in range(1, 6)
}

BROWSER_CLASS_NAMES = {"Chrome_WidgetWin_1"}

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


# ---------- 全局状态 ----------
running = False
paused = False
should_exit = False
preview_window_pinned = False

TARGET_HWND = None

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


# ---------- Win32 封装 ----------
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
user32.EnumWindows.restype = ctypes.c_bool
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = ctypes.c_bool
user32.IsWindow.argtypes = [wt.HWND]
user32.IsWindow.restype = ctypes.c_bool
user32.IsIconic.argtypes = [wt.HWND]
user32.IsIconic.restype = ctypes.c_bool
user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetClientRect.restype = ctypes.c_bool
user32.GetForegroundWindow.restype = wt.HWND
user32.GetDC.argtypes = [wt.HWND]
user32.GetDC.restype = wt.HDC
user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
user32.ReleaseDC.restype = ctypes.c_int
user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, ctypes.c_uint]
user32.PrintWindow.restype = ctypes.c_bool
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.FindWindowW.restype = wt.HWND
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = ctypes.c_bool

gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
gdi32.CreateCompatibleDC.restype = wt.HDC
gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
gdi32.SelectObject.restype = wt.HGDIOBJ
gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
gdi32.DeleteObject.restype = ctypes.c_bool
gdi32.DeleteDC.argtypes = [wt.HDC]
gdi32.DeleteDC.restype = ctypes.c_bool
gdi32.GetDIBits.argtypes = [wt.HDC, wt.HBITMAP, ctypes.c_uint, ctypes.c_uint,
                            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
gdi32.GetDIBits.restype = ctypes.c_int


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wt.DWORD),
        ("biWidth", wt.LONG),
        ("biHeight", wt.LONG),
        ("biPlanes", wt.WORD),
        ("biBitCount", wt.WORD),
        ("biCompression", wt.DWORD),
        ("biSizeImage", wt.DWORD),
        ("biXPelsPerMeter", wt.LONG),
        ("biYPelsPerMeter", wt.LONG),
        ("biClrUsed", wt.DWORD),
        ("biClrImportant", wt.DWORD),
    ]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wt.DWORD * 3),
    ]


# ---------- 基础工具 ----------
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


def get_window_text(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    # 移除零宽字符和其他不可打印字符，避免 GBK 编码错误
    return "".join(c for c in buf.value if c.isprintable() or c.isspace())


def get_class_name(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_window_ready(hwnd):
    return bool(hwnd) and user32.IsWindow(hwnd) and not user32.IsIconic(hwnd)


def clamp_region_to_client(cw, ch):
    CAPTURE_REGION["width"] = clamp(CAPTURE_REGION["width"], 20, max(20, cw))
    CAPTURE_REGION["height"] = clamp(CAPTURE_REGION["height"], 20, max(20, ch))
    CAPTURE_REGION["x"] = clamp(CAPTURE_REGION["x"], 0, max(0, cw - CAPTURE_REGION["width"]))
    CAPTURE_REGION["y"] = clamp(CAPTURE_REGION["y"], 0, max(0, ch - CAPTURE_REGION["height"]))


def _strip_chrome_suffix(title):
    for suffix in (" - Google Chrome", " - Microsoft\u200b Edge", " - Microsoft Edge",
                   " - Chromium", " - Brave"):
        if title.endswith(suffix):
            return title[: -len(suffix)]
    return title


# ---------- 窗口枚举 ----------
def list_browser_windows():
    results = []

    def callback(hwnd, _lp):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = get_window_text(hwnd)
        if not title:
            return True
        if get_class_name(hwnd) in BROWSER_CLASS_NAMES:
            results.append((hwnd, title))
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return results


def pick_target_window():
    global TARGET_HWND
    print("\n=== [1/2] 绑定浏览器窗口（用于截图识别）===")
    print("把目标浏览器切到前台，按 F8 绑定。按 Q 退出。\n")

    windows = list_browser_windows()
    if windows:
        print("当前检测到的 Chrome/Edge 窗口：")
        for hwnd, title in windows:
            print(f"  HWND={hwnd:#x} | {title[:80]}")
    else:
        print("当前未检测到 Chrome/Edge 窗口；打开后再按 F8。")
    print()

    while TARGET_HWND is None:
        if should_exit:
            return None
        time.sleep(0.1)

    return TARGET_HWND


# ---------- 截图 ----------
def capture_window_client(hwnd):
    rect = wt.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return None, 0, 0
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    if w <= 0 or h <= 0:
        return None, 0, 0

    hdc_window = user32.GetDC(hwnd)
    if not hdc_window:
        return None, w, h
    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_window)
        if not hdc_mem:
            return None, w, h
        try:
            hbmp = gdi32.CreateCompatibleBitmap(hdc_window, w, h)
            if not hbmp:
                return None, w, h
            try:
                old = gdi32.SelectObject(hdc_mem, hbmp)
                try:
                    if not user32.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT):
                        return None, w, h

                    bi = BITMAPINFO()
                    bi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                    bi.bmiHeader.biWidth = w
                    bi.bmiHeader.biHeight = -h
                    bi.bmiHeader.biPlanes = 1
                    bi.bmiHeader.biBitCount = 32
                    bi.bmiHeader.biCompression = BI_RGB

                    buf = (ctypes.c_ubyte * (w * h * 4))()
                    got = gdi32.GetDIBits(hdc_mem, hbmp, 0, h,
                                          ctypes.byref(buf), ctypes.byref(bi),
                                          DIB_RGB_COLORS)
                    if got == 0:
                        return None, w, h

                    arr = np.frombuffer(buf, dtype=np.uint8).reshape((h, w, 4))
                    return cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR), w, h
                finally:
                    gdi32.SelectObject(hdc_mem, old)
            finally:
                gdi32.DeleteObject(hbmp)
        finally:
            gdi32.DeleteDC(hdc_mem)
    finally:
        user32.ReleaseDC(hwnd, hdc_window)


# ---------- CDP：HTTP 列 tab + WebSocket 注入按键 ----------
def cdp_list_pages(host=CDP_HOST, port=CDP_PORT, timeout=2.0):
    url = f"http://{host}:{port}/json"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [t for t in data if t.get("type") == "page"]


def cdp_pick_target(window_title_hint="", host=CDP_HOST, port=CDP_PORT):
    """返回 CDP target dict 或 None"""
    print(f"\n=== [2/2] 连接 CDP {host}:{port}（用于注入按键）===")

    if not _WEBSOCKET_AVAILABLE:
        print("[错误] 缺少依赖 websocket-client：pip install websocket-client")
        return None

    try:
        pages = cdp_list_pages(host, port)
    except urllib.error.URLError as e:
        print(f"[错误] 无法连接 CDP {host}:{port}：{e}")
        print(f"请确保 Chrome 启动时加了  --remote-debugging-port={port}")
        print(r'示例： chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-fishing"')
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


def _airdrop_file_candidates(filename):
    base_dir = Path(__file__).resolve().parent
    candidates = [
        Path.cwd() / filename,
        base_dir / filename,
        base_dir.parent / filename,
        base_dir.parent.parent / filename,
    ]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend([
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

    html_mod = __import__("html")
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
    """从 rewards.txt 提取稳定文本和 HTML 特征，避免整段 HTML 精确匹配过脆。"""
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
    """从 hidden.txt 提取大空投任务弹窗特征；此分支只识别，不修改页面。"""
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
    """从 noEnergy.txt 提取无体力弹窗特征；此分支只点击 Buy Energy，不修改 DOM。"""
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
      const ac = /claim/i.test(a.innerText || "") ? 1 : 0;
      const bc = /claim/i.test(b.innerText || "") ? 1 : 0;
      return bc - ac;
    });
  if (buttons.length) {
    buttons[0].click();
    return { found: true, action: "click" };
  }

  let hideNode = root;
  for (let i = 0; i < 3 && hideNode && hideNode.parentElement && hideNode.parentElement !== body; i++) {
    const parentText = hideNode.parentElement.innerText || "";
    if (textMarkers.some((marker) => marker && parentText.includes(marker))) {
      hideNode = hideNode.parentElement;
    }
  }
  if (hideNode && hideNode !== body) {
    hideNode.remove();
    return { found: true, action: "remove" };
  }
  return { found: false, action: "unhandled" };
})()
""" % json.dumps(signature, ensure_ascii=False)

    result = cdp_evaluate(handle_script, timeout=AIR_DROP_CDP_TIMEOUT)
    if isinstance(result, dict) and result.get("found"):
        print("收获小空投")
        return True
    return False


def cdp_detect_hidden_airdrop():
    return _cdp_detect_airdrop_signature(_load_hidden_airdrop_signature())


def cdp_handle_no_energy():
    signature = _load_no_energy_signature()
    if not _cdp_detect_airdrop_signature(signature):
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
  const requiredHtmlHits = Math.min(2, htmlMarkers.length);
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

  const buttons = Array.from(document.querySelectorAll("button,[role='button']"))
    .filter(isVisible)
    .map((el) => ({ el, text: (el.innerText || "").trim() }))
    .filter((item) => /buy\s*energy/i.test(item.text) || (/energy/i.test(item.text) && !/cancel/i.test(item.text)))
    .sort((a, b) => {
      const ae = /^buy\s*energy$/i.test(a.text) ? 1 : 0;
      const be = /^buy\s*energy$/i.test(b.text) ? 1 : 0;
      return be - ae;
    });
  if (!buttons.length) return { found: true, action: "button-not-found" };

  buttons[0].el.click();
  return { found: true, action: "click" };
})()
""" % json.dumps(signature, ensure_ascii=False)

    result = cdp_evaluate(script, timeout=AIR_DROP_CDP_TIMEOUT)
    return isinstance(result, dict) and result.get("action") == "click"


def beep_once():
    try:
        winsound.Beep(1200, 350)
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass


def pause_for_hidden_airdrop():
    global paused
    beep_once()
    paused = True
    print("[空投] 发现大空投，请手动处理任务；脚本已暂停，处理完成后按 F7 继续")


def pause_for_no_energy():
    global paused
    beep_once()
    paused = True
    print("[体力] 检测到无体力，已点击 Buy Energy；脚本已暂停，处理完成后按 F7 继续")


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


def _fetch_tool_items_via_http(auth, timeout=8.0):
    headers = {
        "address": auth["address"],
        "session": auth["session"],
        "avatarversion": auth.get("avatarversion", ""),
        "origin": "https://beta.satworld.io",
        "referer": "https://beta.satworld.io/",
        "accept": "application/json, text/plain, */*",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0"
        ),
        "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Microsoft Edge";v="146"',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-mobile": "?0",
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


def fetch_tool_items_via_cdp():
    work_payload = _fetch_tool_items_via_work_api()
    if isinstance(work_payload, dict) and work_payload.get("ok"):
        return work_payload

    storage = cdp_get_local_storage_items()
    auth_candidates = _extract_auth_candidates_from_storage(storage)
    auth_candidates.sort(
        key=lambda auth: (
            str(auth.get("address") or ""),
        )
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
    return False


def ensure_usable_rod(reason="", force_switch=False):
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
        return ensure_usable_rod("耐久计数归零校准")
    return True


# ---------- 预览置顶 ----------
def pin_preview_window():
    global preview_window_pinned
    if preview_window_pinned:
        return
    try:
        hwnd = user32.FindWindowW(None, PREVIEW_WINDOW_NAME)
        if not hwnd:
            return
        HWND_TOPMOST = -1
        user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0040)
        preview_window_pinned = True
    except Exception:
        pass


# ---------- 鼠标拖框选区 ----------
def mouse_callback(event, x, y, flags, param):
    global dragging, drag_start_x, drag_start_y, temp_region

    scale = param.get("scale", 1.0) or 1.0
    cw = param.get("client_w", 0)
    ch = param.get("client_h", 0)
    xs = int(x / scale)
    ys = int(y / scale)

    if event == cv2.EVENT_LBUTTONDOWN:
        dragging = True
        drag_start_x = xs
        drag_start_y = ys
        temp_region = None
    elif event == cv2.EVENT_MOUSEMOVE and dragging:
        temp_region = {
            "x": min(drag_start_x, xs),
            "y": min(drag_start_y, ys),
            "width": abs(xs - drag_start_x),
            "height": abs(ys - drag_start_y),
        }
    elif event == cv2.EVENT_LBUTTONUP and dragging:
        dragging = False
        if temp_region and temp_region["width"] > 50 and temp_region["height"] > 50:
            CAPTURE_REGION.update({
                "x": temp_region["x"], "y": temp_region["y"],
                "width": temp_region["width"], "height": temp_region["height"],
            })
            if cw and ch:
                clamp_region_to_client(cw, ch)
            print(f"[选区] ({CAPTURE_REGION['x']}, {CAPTURE_REGION['y']}) "
                  f"{CAPTURE_REGION['width']}x{CAPTURE_REGION['height']}")
        temp_region = None


# ---------- 键盘监听 ----------
def on_press(key):
    global running, paused, should_exit, TARGET_HWND, CURRENT_ROD_SLOT, LAST_ROD_SLOTS, ROD_EXPECTED_DURABILITY, SELECTED_AUTH_ADDRESS

    if key == keyboard.Key.f8:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            print("[F8] 未获取到前台窗口")
            return
        cls = get_class_name(hwnd)
        if cls not in BROWSER_CLASS_NAMES:
            print(f"[F8] 前台窗口类名={cls}，不是 Chrome/Edge")
            return
        TARGET_HWND = hwnd
        print(f"[F8] 已绑定 HWND={hwnd:#x} | {get_window_text(hwnd)[:80]}")
        return

    if key == keyboard.Key.f7:
        if TARGET_HWND is None:
            print("[F7] 尚未绑定目标窗口（先按 F8）")
            return
        if _cdp_ws is None:
            print("[F7] 尚未连接 CDP")
            return
        if not running:
            running = True
            paused = False
            CURRENT_ROD_SLOT = None
            LAST_ROD_SLOTS = None
            ROD_EXPECTED_DURABILITY = None
            SELECTED_AUTH_ADDRESS = None
            print("[启动] 开始自动钓鱼")
        else:
            paused = not paused
            print("[暂停]" if paused else "[继续]")
        return

    if key == keyboard.Key.esc:
        if running:
            running = False
            paused = False
            print("[停止]")
        else:
            print("[退出]")
            should_exit = True
        return


listener = keyboard.Listener(on_press=on_press)
listener.start()


# ---------- 识别 ----------
def find_float_target(frame, red_lower, red_upper):
    red_mask = cv2.inRange(frame, red_lower, red_upper)
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < FLOAT_MIN_AREA:
        return None
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


def build_shadow_mask(roi, float_center_local, track_radius, red_lower, red_upper):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    local_median = int(np.median(blurred))
    threshold = max(0, local_median - FISH_BRIGHTNESS_DROP)
    dark = cv2.inRange(blurred, 0, threshold)

    red_mask = cv2.inRange(roi, red_lower, red_upper)
    dark = cv2.bitwise_and(dark, cv2.bitwise_not(red_mask))

    ring = np.zeros_like(dark)
    cv2.circle(ring, float_center_local, track_radius, 255, -1)
    dark = cv2.bitwise_and(dark, ring)

    kernel = np.ones((3, 3), np.uint8)
    dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, kernel)
    dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, kernel)
    return dark, threshold


def contour_overlaps_bite_box(contour, mask_shape, trigger_box_local):
    trigger = np.zeros(mask_shape, dtype=np.uint8)
    cmask = np.zeros(mask_shape, dtype=np.uint8)
    _draw_box_border(trigger, trigger_box_local, 255, FLOAT_BOX_TRIGGER_THICKNESS)
    cv2.drawContours(cmask, [contour], -1, 255, -1)
    return cv2.countNonZero(cv2.bitwise_and(trigger, cmask)) > 0


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


def find_fish_shadow(frame, float_target, red_lower, red_upper):
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
    mask, threshold = build_shadow_mask(roi, local, track_r, red_lower, red_upper)
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


# ---------- 预览 ----------
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


def show_selection_preview():
    if not is_window_ready(TARGET_HWND):
        _draw_placeholder("Target window not ready")
        _check_preview_window()
        return

    frame, cw, ch = capture_window_client(TARGET_HWND)
    if frame is None:
        _draw_placeholder("PrintWindow failed")
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


def refresh_fishing_preview(red_lower, red_upper):
    frame_full, cw, ch = capture_window_client(TARGET_HWND)
    if frame_full is None:
        return None, None, None
    clamp_region_to_client(cw, ch)
    x, y, w, h = CAPTURE_REGION["x"], CAPTURE_REGION["y"], CAPTURE_REGION["width"], CAPTURE_REGION["height"]
    frame = frame_full[y:y + h, x:x + w]
    if frame.size == 0:
        return None, None, None
    ft = find_float_target(frame, red_lower, red_upper)
    fs = find_fish_shadow(frame, ft, red_lower, red_upper)
    show_fishing_preview(frame, ft, fs)
    return frame, ft, fs


def wait_with_preview(duration, red_lower, red_upper):
    end = time.time() + duration
    while time.time() < end:
        if should_exit or paused or not running:
            return False
        if user32.IsIconic(TARGET_HWND):
            return False
        refresh_fishing_preview(red_lower, red_upper)
        remaining = end - time.time()
        time.sleep(min(0.05, max(remaining, 0)))
    return True


# ---------- 主循环 ----------
def main():
    global should_exit, _cdp_target_cache, CDP_PORT, CDP_HOST, PREVIEW_WINDOW_NAME, TARGET_HWND

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='自动钓鱼脚本 - 支持多账号')
    parser.add_argument('--port', type=int, default=9222, help='CDP 调试端口（默认 9222）')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='CDP 主机地址（默认 127.0.0.1）')
    parser.add_argument('--name', type=str, default='', help='实例名称，用于区分不同账号')
    parser.add_argument('--auto-bind', action='store_true', help='自动绑定浏览器窗口，不需要按 F8')
    args = parser.parse_args()

    # 更新全局配置
    CDP_PORT = args.port
    CDP_HOST = args.host
    instance_name = args.name
    auto_bind = args.auto_bind

    # 根据实例名称更新窗口标题
    if instance_name:
        PREVIEW_WINDOW_NAME = f"Fishing Preview - {instance_name}"
    else:
        PREVIEW_WINDOW_NAME = f"Fishing Preview - Port {CDP_PORT}"

    print(f"=== 自动钓鱼脚本 0.5（CDP 注入版）===")
    if instance_name:
        print(f"实例名称: {instance_name}")
    print(f"CDP 端口: {CDP_HOST}:{CDP_PORT}")
    print()
    print("先决条件：")
    print(f'  Chrome 启动时需带参数 --remote-debugging-port={CDP_PORT}')
    print(f'  推荐： chrome.exe --remote-debugging-port={CDP_PORT} --user-data-dir="%TEMP%\\chrome-fishing-{CDP_PORT}"')
    print("  pip install websocket-client")
    print()

    if auto_bind:
        print("=== [1/2] 自动绑定浏览器窗口 ===")
        # 自动查找并绑定浏览器窗口
        windows = list_browser_windows()
        if not windows:
            print("[错误] 未检测到 Chrome/Edge 窗口")
            print("请先启动浏览器，然后重新运行脚本")
            return

        # 如果只有一个窗口，直接绑定
        if len(windows) == 1:
            TARGET_HWND = windows[0][0]
            print(f"[自动绑定] 已绑定唯一的浏览器窗口")
            print(f"  HWND={TARGET_HWND:#x} | {windows[0][1][:80]}")
        else:
            # 多个窗口，根据端口号按顺序绑定
            print(f"检测到 {len(windows)} 个浏览器窗口：")
            for i, (hwnd, title) in enumerate(windows):
                print(f"  [{i}] HWND={hwnd:#x} | {title[:80]}")

            # 根据端口号计算窗口索引
            # 端口 9222 -> 索引 0 (第一个窗口)
            # 端口 9223 -> 索引 1 (第二个窗口)
            # 端口 9224 -> 索引 2 (第三个窗口)
            window_index = CDP_PORT - 9222

            if 0 <= window_index < len(windows):
                TARGET_HWND = windows[window_index][0]
                print(f"\n[自动绑定] 根据端口 {CDP_PORT} 绑定第 {window_index + 1} 个窗口")
                print(f"  HWND={TARGET_HWND:#x} | {windows[window_index][1][:80]}")
            else:
                # 如果索引超出范围，绑定第一个窗口
                TARGET_HWND = windows[0][0]
                print(f"\n[自动绑定] 端口 {CDP_PORT} 超出范围，绑定第一个窗口")
                print(f"  HWND={TARGET_HWND:#x} | {windows[0][1][:80]}")
        print()
    else:
        print("操作：F8 绑定窗口 → 选 tab → 拖框选区 → F7 启动/暂停 → ESC 停止/退出")
        print("提示：浏览器窗口可被遮挡；但目标 tab 应保持 active，否则 Chrome 会 throttle JS")
        print()

        # 手动绑定模式
        pick_target_window()
        if should_exit or TARGET_HWND is None:
            return

    target = cdp_pick_target(window_title_hint=get_window_text(TARGET_HWND), host=CDP_HOST, port=CDP_PORT)
    if target is None:
        print("[终止] 未能获取 CDP target")
        return
    _cdp_target_cache = target
    try:
        cdp_connect(target)
    except Exception as e:
        print(f"[终止] CDP 连接失败：{e}")
        return

    red_lower = np.array([0, 0, 100])
    red_upper = np.array([80, 80, 255])

    cv2.namedWindow(PREVIEW_WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(PREVIEW_WINDOW_NAME, mouse_callback, MOUSE_PARAM)

    while not should_exit:
        if not user32.IsWindow(TARGET_HWND):
            print("[错误] 目标窗口已关闭")
            break

        if user32.IsIconic(TARGET_HWND):
            _draw_placeholder("Target minimized - waiting...")
            _check_preview_window()
            time.sleep(0.5)
            continue

        if not running:
            show_selection_preview()
            time.sleep(0.05)
            continue

        if paused:
            refresh_fishing_preview(red_lower, red_upper)
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
            if user32.IsIconic(TARGET_HWND):
                break
            _, _, fs = refresh_fishing_preview(red_lower, red_upper)
            if time.time() < detect_after:
                time.sleep(random_delay(0.04, 0.08))
                continue
            if fish_touching_float(fs):
                r_delay = gaussian_delay(0.13, 0.17)
                print(f"[检测] 咬钩！反应 {r_delay:.2f}s")
                bite = True
                if not wait_with_preview(r_delay, red_lower, red_upper):
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
            if wait_with_preview(reel_delay, red_lower, red_upper):
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
