"""
钓鱼机器人 - 配置文件
包含所有常量和配置项
"""

# 窗口和显示配置
PREVIEW_WINDOW_NAME = "Fishing Preview"
CAPTURE_REGION = {"x": 0, "y": 0, "width": 355, "height": 159}

# 图像识别参数
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

# 钓鱼时间参数
CAST_BITE_DETECTION_DELAY = 2.0  # 抛竿后开始检测咬钩的延迟

# 弹窗检测文件
AIR_DROP_REWARD_FILE = "rewards.txt"
HIDDEN_AIRDROP_FILE = "hidden.txt"
NO_ENERGY_FILE = "noEnergy.txt"
AIR_DROP_CDP_TIMEOUT = 0.8
AIR_DROP_HANDLE_DELAY = 0.2

# 鱼竿切换参数
ROD_SWITCH_KEY_PRESSES = 2
ROD_SWITCH_PRE_KEY_DELAY = (0.16, 0.24)
ROD_SWITCH_KEY_INTERVAL = (0.08, 0.12)
ROD_SWITCH_SETTLE_DELAY = 0.8

# Windows API 常量
PW_RENDERFULLCONTENT = 0x00000002
DIB_RGB_COLORS = 0
BI_RGB = 0

# 按键定义
KEY_F = {"vk": 0x46, "code": "KeyF", "key": "f"}
KEY_DIGITS = {
    slot: {"vk": 0x30 + slot, "code": f"Digit{slot}", "key": str(slot)}
    for slot in range(1, 6)
}

# 浏览器配置
BROWSER_CLASS_NAMES = {"Chrome_WidgetWin_1"}

# CDP 配置
CDP_HOST = "127.0.0.1"
CDP_PORT = 9222

# API 配置
API_USER_ITEM_URL = "https://api.satworld.io/game/user-item"
TOOL_SINGLE_TYPE_ORDER = {
    "FishingPole": 0,
    "Axe": 1,
    "Pickaxe": 2,
}
TOOL_TEXT_MARKERS = ("rod", "fishing", "axe", "pickaxe", "钓", "竿", "斧", "镐")
