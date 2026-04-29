"""
钓鱼机器人 - 工具函数模块
包含通用的辅助函数
"""
import random


def random_delay(a, b):
    """生成随机延迟时间"""
    return random.uniform(a, b)


def gaussian_delay(a, b):
    """生成高斯分布的延迟时间"""
    center = (a + b) / 2
    sigma = (b - a) / 6
    return clamp(random.gauss(center, sigma), a, b)


def clamp(v, lo, hi):
    """限制值在指定范围内"""
    return max(lo, min(v, hi))


def beep_once():
    """发出提示音"""
    import winsound
    try:
        winsound.Beep(1200, 350)
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
