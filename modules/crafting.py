"""
装备制作模块
负责自动制作装备(钓鱼竿等)
"""

import asyncio
import json
import time


class CraftingManager:
    """装备制作管理器"""

    # DOM选择器常量
    CRAFTING_ITEMS_SELECTOR = '.sc-ce13daa3-2'  # 制作栏物品
    ITEM_TITLE_SELECTOR = '.sc-42cfac2f-3.hUsZvD'  # 物品标题
    CONFIRM_BUTTON_SELECTOR = 'button.sc-64321481-5.dDNZgN.confirm'  # 确认按钮

    # 时间间隔常量
    OPEN_CRAFTING_DELAY = 0.5  # 打开制作台后的延迟(秒)
    STEP_DELAY = 0.5  # 每步操作之间的延迟(秒)
    CRAFTING_COOLDOWN = 7.0  # 制作冷却时间(秒)
    WAIT_CRAFTING_OPEN_TIMEOUT = 5.0  # 等待制作台打开的超时时间(秒)
    WAIT_CRAFTING_OPEN_INTERVAL = 0.2  # 等待制作台打开的检查间隔(秒)

    def __init__(self, cdp_send_func, send_key_func):
        """
        初始化制作管理器

        Args:
            cdp_send_func: CDP发送函数,用于执行JavaScript
            send_key_func: 发送按键函数,用于发送F键等
        """
        self.cdp_send = cdp_send_func
        self.send_key = send_key_func
        self.is_crafting = False
        self.target_count = 0
        self.current_count = 0

    async def start_crafting(self, count, item_keyword="Rod"):
        """
        开始制作装备

        Args:
            count: 要制作的数量
            item_keyword: 物品关键词,默认为"Rod"(钓鱼竿)

        Returns:
            bool: 是否成功完成制作
        """
        self.is_crafting = True
        self.target_count = count
        self.current_count = 0

        print(f"[制作] 开始制作 {count} 个装备(关键词: {item_keyword})")

        try:
            while self.is_crafting and self.current_count < self.target_count:
                # 执行一次制作流程
                success = await self._craft_once(item_keyword)

                if success:
                    self.current_count += 1
                    print(f"[制作] 进度: {self.current_count}/{self.target_count}")
                else:
                    print(f"[制作] 第 {self.current_count + 1} 次制作失败")

                # 如果还需要继续制作,等待冷却时间
                if self.current_count < self.target_count:
                    await asyncio.sleep(self.CRAFTING_COOLDOWN)

            print(f"[制作] 完成! 共制作 {self.current_count}/{self.target_count} 个装备")
            return self.current_count == self.target_count

        except Exception as e:
            print(f"[制作] 发生错误: {e}")
            return False
        finally:
            self.is_crafting = False

    async def _wait_for_crafting_open(self):
        """
        等待制作台打开

        Returns:
            bool: 是否成功打开
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # 检查是否超时
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.WAIT_CRAFTING_OPEN_TIMEOUT:
                print(f"[制作] 等待制作台打开超时")
                return False

            # 检查制作栏是否存在
            js_code = f"""
            (function() {{
                const items = document.querySelectorAll('{self.CRAFTING_ITEMS_SELECTOR}');
                return items && items.length > 0;
            }})()
            """
            result = await self.cdp_send("Runtime.evaluate", {
                "expression": js_code,
                "returnByValue": True
            })

            if result is None:
                await asyncio.sleep(self.WAIT_CRAFTING_OPEN_INTERVAL)
                continue

            # 检查CDP层面的错误
            if "error" in result:
                await asyncio.sleep(self.WAIT_CRAFTING_OPEN_INTERVAL)
                continue

            # 获取result字段
            result_data = result.get("result", {})

            # 检查JavaScript执行异常
            if "exceptionDetails" in result_data:
                await asyncio.sleep(self.WAIT_CRAFTING_OPEN_INTERVAL)
                continue

            # 获取实际的返回值
            inner_result = result_data.get("result", {})
            value = inner_result.get("value")

            if value == True:
                print(f"[制作] 制作台已打开")
                return True

            # 继续等待
            await asyncio.sleep(self.WAIT_CRAFTING_OPEN_INTERVAL)

    async def _craft_once(self, item_keyword):
        """
        执行一次制作流程

        Args:
            item_keyword: 物品关键词

        Returns:
            bool: 是否成功
        """
        try:
            # 1. 发送F键打开制作台
            await self.send_key({"vk": 0x46, "code": "KeyF", "key": "f"})
            print(f"[制作] 发送F键打开制作台")

            # 2. 等待制作台打开
            if not await self._wait_for_crafting_open():
                print(f"[制作] 制作台未能打开")
                return False

            await asyncio.sleep(self.STEP_DELAY)

            # 3. 点击第3个制作栏div
            click_result = await self._click_crafting_item(2)  # 索引2 = 第3个
            if not click_result:
                print(f"[制作] 点击制作栏失败")
                return False

            await asyncio.sleep(self.STEP_DELAY)  # 等待界面弹出

            # 4. 查找并验证包含关键词的物品
            item_found = await self._find_item_by_keyword(item_keyword)
            if not item_found:
                print(f"[制作] 未找到包含 '{item_keyword}' 的物品")
                return False

            await asyncio.sleep(self.STEP_DELAY)  # 等待验证完成

            # 5. 点击Confirm按钮
            confirm_result = await self._click_confirm_button()
            if not confirm_result:
                print(f"[制作] 点击Confirm按钮失败")
                return False

            print(f"[制作] 制作成功")
            return True

        except Exception as e:
            print(f"[制作] 制作流程出错: {e}")
            return False

    async def _click_crafting_item(self, index):
        """
        点击制作栏中的第N个物品

        Args:
            index: 物品索引(0-based)

        Returns:
            bool: 是否成功
        """
        js_code = f"""
        (function() {{
            const items = document.querySelectorAll('{self.CRAFTING_ITEMS_SELECTOR}');
            console.log('[制作] 找到制作栏物品数量:', items.length);
            if (items && items.length > {index}) {{
                console.log('[制作] 点击第', {index}, '个物品');
                items[{index}].click();
                return true;
            }}
            console.log('[制作] 制作栏物品不足');
            return false;
        }})()
        """
        result = await self.cdp_send("Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True
        })

        # 调试输出
        print(f"[制作调试] CDP返回结果: {result}")

        if result is None:
            return False

        # 检查CDP层面的错误
        if "error" in result:
            print(f"[制作] CDP错误: {result['error']}")
            return False

        # 获取result字段
        result_data = result.get("result", {})

        # 检查JavaScript执行异常
        if "exceptionDetails" in result_data:
            print(f"[制作] JavaScript执行出错: {result_data['exceptionDetails']}")
            return False

        # 获取实际的返回值 (result.result.value)
        inner_result = result_data.get("result", {})
        value = inner_result.get("value")
        print(f"[制作调试] 返回值: {value}")

        return value == True

    async def _find_item_by_keyword(self, keyword):
        """
        查找包含关键词的物品

        Args:
            keyword: 关键词

        Returns:
            bool: 是否找到
        """
        js_code = f"""
        (function() {{
            const titles = document.querySelectorAll('{self.ITEM_TITLE_SELECTOR}');
            console.log('[制作] 找到物品标题数量:', titles.length);
            for (let title of titles) {{
                console.log('[制作] 物品标题:', title.textContent);
                if (title.textContent.includes('{keyword}')) {{
                    console.log('[制作] 找到匹配的物品:', title.textContent);
                    return true;
                }}
            }}
            console.log('[制作] 未找到匹配的物品');
            return false;
        }})()
        """
        result = await self.cdp_send("Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True
        })

        if result is None:
            return False

        # 检查CDP层面的错误
        if "error" in result:
            print(f"[制作] CDP错误: {result['error']}")
            return False

        # 获取result字段
        result_data = result.get("result", {})

        # 检查JavaScript执行异常
        if "exceptionDetails" in result_data:
            print(f"[制作] JavaScript执行出错: {result_data['exceptionDetails']}")
            return False

        # 获取实际的返回值 (result.result.value)
        inner_result = result_data.get("result", {})
        value = inner_result.get("value")
        print(f"[制作调试] 查找物品返回值: {value}")

        return value == True

    async def _click_confirm_button(self):
        """
        点击Confirm按钮

        Returns:
            bool: 是否成功
        """
        js_code = f"""
        (function() {{
            const button = document.querySelector('{self.CONFIRM_BUTTON_SELECTOR}');
            console.log('[制作] 查找Confirm按钮:', button);
            if (button) {{
                console.log('[制作] 点击Confirm按钮');
                button.click();
                return true;
            }}
            console.log('[制作] 未找到Confirm按钮');
            return false;
        }})()
        """
        result = await self.cdp_send("Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True
        })

        print(f"[制作调试] Confirm按钮CDP返回结果: {result}")

        if result is None:
            return False

        # 检查CDP层面的错误
        if "error" in result:
            print(f"[制作] CDP错误: {result['error']}")
            return False

        # 获取result字段
        result_data = result.get("result", {})

        # 检查JavaScript执行异常
        if "exceptionDetails" in result_data:
            print(f"[制作] JavaScript执行出错: {result_data['exceptionDetails']}")
            return False

        # 获取实际的返回值 (result.result.value)
        inner_result = result_data.get("result", {})
        value = inner_result.get("value")
        print(f"[制作调试] Confirm按钮返回值: {value}")

        return value == True

    def stop_crafting(self):
        """停止制作"""
        self.is_crafting = False
        print(f"[制作] 已停止制作")

