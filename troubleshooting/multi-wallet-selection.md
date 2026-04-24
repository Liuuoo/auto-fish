# AF-003：多钱包 session 导致读取到错误账号

状态：已解决

## 问题描述

浏览器 localStorage 中可能同时存在多个钱包的 `address_session`。脚本请求 `/game/user-item` 时，如果自动选择了错误 session，就会读取到非当前游戏账号的快捷栏和鱼竿耐久。

## 现象

- 日志只显示某一个错误快捷栏，例如 `5:8/10`。
- 用户实际游戏装备栏并不是这个状态。
- 同一浏览器里存在多个钱包或多个账号登录痕迹时更容易出现。

## 根因

- localStorage 中同时保留多个 `address_session`。
- “页面最近请求地址”“接口返回物品数量”“快捷栏鱼竿最完整”都只是间接信号，不能稳定代表当前游戏账号。
- 自动猜账号会在多钱包场景下读错 `/game/user-item`。

## 当前解决方案

- 多钱包时不再自动猜账号。
- 检测到多个 session 后，程序列出编号和地址后 5 位，例如 `...abcde`。
- 用户输入编号后，本次运行固定使用该钱包请求 `/game/user-item`。
- 重新按 `F7` 启动新一轮自动钓鱼时，会清空已选钱包并重新选择，避免切换账号后沿用旧状态。

## 涉及代码

- `_extract_auth_candidates_from_storage(storage)`
- `_choose_auth_candidate(auth_candidates)`
- `SELECTED_AUTH_ADDRESS`
- `fetch_tool_items_via_cdp()`

## 后续维护边界

- 不要用“鱼竿数量最多”“快捷栏最完整”“最近请求地址”自动选择钱包。
- 多钱包时必须显式选择。
- 如果未来能从游戏页面可靠读取当前钱包地址，可以替代手动选择；在此之前不要恢复自动猜测。
