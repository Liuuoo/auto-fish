# SatWorld 游戏 API 完整参考手册

> **数据来源**：项目 `rod_manager.py` 已用 API + 历史 F12 网络抓包分析 (Session `20260315_043116`)
> 
> **Base URL**：`https://api.satworld.io`
> 
> **游戏前端**：`https://beta.satworld.io`

---

## 通用认证机制

所有 API 请求需要在 **Request Headers** 中携带以下字段：

| Header 字段 | 说明 | 示例 |
|:---|:---|:---|
| `address` | 玩家钱包地址 (bc1p...) | `bc1pcpr5uvw7d5vm...setzhza` |
| `session` | 32位十六进制会话令牌 | `dffa0fa857fe433cb7b16456868f34f1` |
| `avatarversion` | 客户端版本号 | `v0.3.3` |
| `origin` | 来源域名 | `https://beta.satworld.io` |
| `referer` | 引用页 | `https://beta.satworld.io/` |
| `sw` | **请求签名**（仅 POST 请求） | Base64 编码的动态签名串 |

> [!WARNING]
> **`sw` 签名字段**是最关键的安全机制。它是一个动态生成的 Base64 编码字符串，随每个 POST 请求变化，用于后端验证请求完整性。**GET 请求（如查询背包）不需要此字段**，但 POST 请求（如合成、绑定快捷键）必须带上，否则会被服务器拒绝。逆向此签名的生成算法需要分析前端混淆 JS。

### 通用响应格式

```json
{
  "code": 1,          // 1 = 成功, 其他 = 失败
  "msg": "success",   // 业务消息
  "data": { ... }     // 业务数据
}
```

---

## 一、资产系统 (Inventory & Resource)

### 1.1 查询装备/工具背包

获取玩家拥有的所有工具类物品（鱼竿、斧头、镐等），包含耐久度和快捷栏绑定信息。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/user-item` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` |
| **当前使用** | ✅ 已在 `rod_manager.py` 中使用 |

**响应示例** (`data.packResult` 数组):

```json
{
  "code": 1,
  "data": {
    "packResult": [
      {
        "userItemId": "69b15aa2...",       // 物品实例唯一ID (数据库索引)
        "name": "fishingrod_t4_01",         // 物品内部名 (模型ID)
        "description": "Shining Golden Rod",// 中文/显示名称
        "singleType": "FishingPole",        // 物品类型
        "tag": 351,                         // 物品标识码
        "currentDurability": 14,            // 当前耐久
        "maxDurability": 15,                // 最大耐久
        "shortcut": "1",                    // 快捷栏位置 (1-5), 空=未绑定
        "isNew": false                      // 是否是新获取的物品
      },
      {
        "userItemId": "69b010b5...",
        "name": "axe_t4_01",
        "description": "Shining Golden Axe",
        "singleType": "Axe",
        "tag": 151,
        "currentDurability": 8,
        "maxDurability": 25,
        "shortcut": "4",
        "isNew": false
      }
    ]
  }
}
```

**已知 `singleType` 类型**：

| singleType | 说明 |
|:---|:---|
| `FishingPole` | 钓竿 |
| `Axe` | 斧头 |
| `Pickaxe` | 镐（推测） |

---

### 1.2 查询材料/资源背包

获取玩家拥有的所有原材料类物品（木头、石头、鱼肉等）。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/umi/list` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` |
| **当前使用** | ❌ 未使用 |

**响应示例** (`data` 数组):

```json
{
  "code": 1,
  "data": [
    { "tag": 10101, "name": "Wood",     "count": 3678 },
    { "tag": 10201, "name": "Stone",    "count": 2911 },
    { "tag": 10301, "name": "Fish_01",  "count": 234 },
    { "tag": 10302, "name": "Fish_02",  "count": 189 },
    { "tag": 10307, "name": "Fish_07",  "count": 1634 }
  ]
}
```

---

## 二、合成/制造系统 (Synthesis)

### 2.1 查询合成配方列表

获取所有可制造的工具及其所需材料。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/synthesis/list` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` (推测) |
| **当前使用** | ❌ 未使用 |

**响应特征**：返回树状合成关系链，包含每个成品的 `tag`、材料需求（低级工具 + 基础资源）和合成代价。

---

### 2.2 执行合成/制造

根据配方标签创建（合成）一个新物品。

| 项目 | 内容 |
|:---|:---|
| **URL** | `POST /game/synthesis/create/{synthesisTag}` |
| **认证** | `address` + `session`（Header） |
| **签名** | ⚠️ **需要 `sw` 签名** |
| **当前使用** | ❌ 未使用 |

**路径参数**：

| 参数 | 说明 | 示例 |
|:---|:---|:---|
| `synthesisTag` | 目标成品的合成标签 | `10001` (金斧头), `10002` (达人斧头) |

**已知合成链条** (从抓包分析)：

```
基础材料 (Wood/Stone) + 低级工具 → 中级工具 → 高级工具

示例：合成金斧头 (tag: 10001)
  需要：1x 达人斧头 (tag: 102) + 5x 木头 (tag: 10101)

示例：合成达人斧头 (tag: 10002)
  需要：（具体配方需查询 synthesis/list）
```

> [!IMPORTANT]
> 合成成功后，客户端会**立即触发** `/game/synthesis/list` 刷新状态（防抖机制）。脚本中进行自动合成时也应在合成后刷新背包。

---

## 三、快捷栏绑定系统

### 3.1 设置装备快捷键

将物品绑定到快捷栏的指定位置（1-5）。

| 项目 | 内容 |
|:---|:---|
| **URL** | `POST /game/user-item/set-equipment-shortcut` |
| **认证** | `address` + `session`（Header） |
| **签名** | ⚠️ **需要 `sw` 签名** |
| **当前使用** | ❌ 未使用 |

**请求参数** (Body 或 Query):

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| `userItemId` | string | 物品实例唯一 ID（来自 `user-item` 接口） |
| `shortcut` | string/number | 快捷栏位置 (`1`-`5`) |

**应用场景**：
- 工具耐久归零后，自动将备用工具绑定到空出的快捷栏位
- 合成新工具后，自动装备到快捷栏

---

## 四、任务系统 (Task)

### 4.1 查询任务进度

获取玩家当前所有任务（每日任务 + 社区任务）的完成进度。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/task/progress-list` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` |
| **当前使用** | ❌ 未使用 |

**响应特征**：

```json
{
  "code": 1,
  "data": {
    "daily": [
      {
        "taskId": "DailyToolConsumption",
        "description": "消耗 2 个工具",
        "currentCount": 2,
        "requiredCount": 2,
        "status": "completed",
        "reward": { "tag": 10307, "count": 5 }
      },
      {
        "taskId": "CraftingMaster",
        "description": "制作 10 次工具",
        "currentCount": 10,
        "requiredCount": 10,
        "status": "completed"
      }
    ],
    "community": [
      {
        "taskId": "CommunityDropTask",
        "description": "社区贡献积分获代币奖励",
        "subTasks": [
          { "id": "ConsumeEnergy", "current": 60, "required": 60 },
          { "id": "CommitMaterial", "current": 0, "required": 200 }
        ]
      }
    ]
  }
}
```

**自动化价值**：
- 监控 `currentCount` vs `requiredCount`，实现**任务自动提醒**
- 监控 `CommunityDropTask` 出现/状态变化，实现**空投自动提示**

---

## 五、排名系统 (Rank)

### 5.1 批量查询活动排名

获取当前服务器活动排行榜数据。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/activity-rank/batch-rlt` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` |
| **当前使用** | ❌ 未使用 |

**请求参数**：

| 参数 | 说明 |
|:---|:---|
| `activityTags` | 活动标签，区分不同排行榜 |

**响应特征**：返回 Top 20 玩家排名，包含钱包地址和积分。

---

## 六、装扮系统 (Cosmetics)

### 6.1 查询可用装扮

检查玩家钱包中持有的 NFT 装扮资产。

| 项目 | 内容 |
|:---|:---|
| **URL** | `GET /game/address-usable` |
| **认证** | `address` + `session`（Header） |
| **签名** | ❌ 不需要 `sw` |
| **当前使用** | ❌ 未使用 |

**响应特征**：返回玩家拥有的装扮列表（发型、上衣、裤子、鞋子、头饰等），每项关联 `inscriptionId`（链上铭文 ID）。

---

## 物品标识码 (Tag) 速查表

基于已截获的数据，整理的已知 Tag 编码：

### 工具类

| Tag | 物品名 | 类别 |
|:---|:---|:---|
| `151` | Shining Golden Axe (金斧头) | Axe |
| `102` | Daredevil Axe (达人斧头) | Axe |
| `351` | Shining Golden Rod (金钓竿) | FishingPole |

### 材料类

| Tag | 物品名 | 说明 |
|:---|:---|:---|
| `10101` | Wood (木头) | 基础资源 |
| `10201` | Stone (石头) | 基础资源 |
| `10301` | Fish_01 | 鱼类 |
| `10302` | Fish_02 | 鱼类 |
| `10303` | Fish_03 | 鱼类 |
| `10304` | Fish_04 | 鱼类 |
| `10305` | Fish_05 | 鱼类 |
| `10306` | Fish_06 | 鱼类 |
| `10307` | Fish_07 | 鱼类 (最高产出/最常见) |

### 合成配方 Tag

| synthesisTag | 产出 | 已知配方 |
|:---|:---|:---|
| `10001` | 金斧头 | 1x 达人斧头(102) + 5x 木头(10101) |
| `10002` | 达人斧头 | 需查询 `/game/synthesis/list` |

> [!NOTE]
> 上表仅为已截获的部分数据。完整 Tag 编码需通过调用 `/game/synthesis/list` 和 `/game/umi/list` 获取全量数据。

---

## WebSocket 实时通讯协议

除 HTTP API 外，游戏还通过 WebSocket 进行实时通讯：

| 协议层 | 技术 |
|:---|:---|
| **传输框架** | Socket.IO (EIO=4) |
| **序列化** | Protobuf (部分嵌套 JSON) |

### 核心报文类型

| Protobuf ID | 名称 | 方向 | 说明 |
|:---|:---|:---|:---|
| `2001` | 移动同步包 | 双向 | 包含角色 X/Y/Z 坐标 |
| `3101` | 心跳/状态包 | 双向 | 每秒 1-2 次，维持在线 |
| - | 实体同步包 | 服务器→客户端 | 推送周围玩家和物品状态 |

---

## 自动化场景路线图

基于上述 API，以下是可实现的自动化功能：

### ✅ 已实现（当前代码）
1. **查看背包鱼竿耐久** → `GET /game/user-item`
2. **自动换竿** → 检测耐久后按键切换 (物理按键)

### 🟡 可直接实现（GET 请求，无需签名）
3. **查看全部材料库存** → `GET /game/umi/list`
4. **查看合成配方** → `GET /game/synthesis/list`
5. **监控任务进度** → `GET /game/task/progress-list`
6. **查看活动排名** → `GET /game/activity-rank/batch-rlt`
7. **查看装扮资产** → `GET /game/address-usable`

### 🔴 需攻克签名（POST 请求，需要 `sw` 签名）
8. **自动合成/造工具** → `POST /game/synthesis/create/{tag}` ⚠️
9. **自动绑定快捷栏** → `POST /game/user-item/set-equipment-shortcut` ⚠️

> [!CAUTION]
> POST 类操作需要逆向前端 JS 中 `sw` 签名的生成算法。在此之前，可通过 **Playwright 拦截浏览器请求**的方式间接获取带签名的请求头来实现自动化，或者通过**模拟键盘操作游戏 UI** 来绕过 API 层面的签名检查。
