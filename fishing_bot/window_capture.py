"""
钓鱼机器人 - 窗口捕获模块
处理 Windows 窗口截图和窗口管理
"""
import ctypes
import ctypes.wintypes as wt
import cv2
import numpy as np

from .config import PW_RENDERFULLCONTENT, DIB_RGB_COLORS, BI_RGB, BROWSER_CLASS_NAMES


# ---------- Win32 API 封装 ----------
user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)

# 设置函数签名
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
    """位图信息头结构"""
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
    """位图信息结构"""
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wt.DWORD * 3),
    ]


def get_window_text(hwnd):
    """获取窗口标题"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    # 移除零宽字符和其他不可打印字符
    return "".join(c for c in buf.value if c.isprintable() or c.isspace())


def get_class_name(hwnd):
    """获取窗口类名"""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def is_window_ready(hwnd):
    """检查窗口是否准备就绪"""
    return bool(hwnd) and user32.IsWindow(hwnd) and not user32.IsIconic(hwnd)


def list_browser_windows():
    """列出所有浏览器窗口"""
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


def capture_window_client(hwnd):
    """
    截取窗口客户区
    返回: (frame, width, height)
    """
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
