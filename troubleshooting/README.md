# 问题记录索引

本目录采用“1 + N”结构维护历史问题。

- `README.md` 是总索引，只记录问题描述、解决状态和解决文档入口。
- 每个具体问题单独维护一个解决文档，避免 README 变成长篇维护日志。
- 新问题优先新增独立文档，再把索引表补一行。

## 问题列表

| ID | 问题描述 | 状态 | 解决文档 |
| --- | --- | --- | --- |
| AF-001 | 每轮点击数字快捷键导致鱼竿状态不稳定，日志显示切换但游戏未必切换 | 已解决 | [rod-slot-switching.md](rod-slot-switching.md) |
| AF-002 | 脚本收竿计数和游戏真实耐久可能不一致 | 已解决 | [durability-counter-state.md](durability-counter-state.md) |
| AF-003 | 多钱包 session 导致读取到错误账号的鱼竿耐久 | 已解决 | [multi-wallet-selection.md](multi-wallet-selection.md) |
| AF-004 | 抛竿瞬间误判咬钩，刚抛竿就立刻收竿 | 已解决 | [cast-bite-cooldown.md](cast-bite-cooldown.md) |
| AF-005 | 鱼竿耐久归零后立即切换下一根鱼竿失败 | 已解决 | [rod-zero-switch-timing.md](rod-zero-switch-timing.md) |

## 维护约定

- 问题描述要写可观察现象，不只写代码层结论。
- 解决文档必须包含：现象、根因、当前方案、涉及代码、后续维护边界。
- 状态只使用：`未解决`、`临时规避`、`已解决`。
- 不要把多个独立问题合并到同一个解决文档；如果一个问题引出了新问题，应新增文档并互相引用。
