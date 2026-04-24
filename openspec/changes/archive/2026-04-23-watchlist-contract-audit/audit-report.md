# Watchlist 服务端化契约核查报告

## 后端路由现状

文件：`investment-back/src/api/v1/watchlist.py`

| 方法 | 路径 | ID 类型 | 返回 Schema | 状态 |
|------|------|---------|------------|------|
| GET | `/api/v1/watchlist` | — | `List[WatchlistItem]` | ✅ 可用 |
| POST | `/api/v1/watchlist` | — | `WatchlistItem` | ✅ 可用 |
| PUT | `/api/v1/watchlist/{item_id}` | `int` | `WatchlistItem` | ✅ 可用 |
| DELETE | `/api/v1/watchlist/{item_id}` | `int` | `{"message": ...}` | ✅ 可用 |

**服务层**：`investment-back/src/services/watchlist_service.py`
- `get_watchlist(user_id)`：返回 `List[WatchlistItem]`（对应 `watchlist_items_legacy` 表）
- `add_to_watchlist`：幂等 upsert，若已存在直接返回已有记录
- `update_watchlist_item`：仅更新 `focus_reason`
- `remove_from_watchlist`：物理删除

**权限边界**：所有路由均依赖 `get_current_user`，user_id 隔离 ✅

---

## 数据模型现状：两套表并存

| 表名 | ID 类型 | 状态 | 说明 |
|------|---------|------|------|
| `watchlist_items_legacy` | `Integer` | 活跃（API 直接使用） | 旧表，API 路由读写此表 |
| `watchlists` | `UUID` | 存在但 API 未接入 | v2 表，有更丰富的字段（`added_from_scenario`、`source_analysis_id`、`notify_on_events`） |

**关键矛盾**：`GET /api/v1/watchlist` 读写的是 `watchlist_items_legacy`（int ID），但新设计的 `watchlists`（UUID ID）才是后续主表。两套表并存，前端接入当前 API 会直接绑定到旧表。

---

## 字段映射表：后端 vs 前端

| 字段 | 后端 `WatchlistItem` Schema | 前端 `WatchlistItem` Type | 是否一致 |
|------|---------------------------|--------------------------|---------|
| `id` | `int` | `string` | ❌ **类型冲突** |
| `stock_id` | `string` ✅ | `string` ✅ | ✅ |
| `focus_reason` | `string?` ✅ | `string?` ✅ | ✅ |
| `created_at` | `datetime` ✅ | —（前端不存） | ✅ 可忽略 |
| `updated_at` | `datetime` ✅ | —（前端不存） | ✅ 可忽略 |
| `stock_name` | ❌ 不在 schema | `string` | ❌ 缺失 |
| `market` | ❌ 不在 schema | `string` | ❌ 缺失 |
| `industry` | ❌ 不在 schema | `string?` | ❌ 缺失 |
| `added_at` | ❌（用 `created_at`） | `string` | ❌ 字段名不同 |

---

## 契约差异对照表

| 字段 | legacy API 响应 | v2 表实际字段 | 前端展示需要 | 是否阻塞切换 |
|------|----------------|-------------|------------|------------|
| `id` | `int` ✅ | `UUID` | `string`（前端现有） | ❌ 阻塞（B1a 需统一 UUID） |
| `stock_id` | `string` ✅ | `string` ✅ | `string` ✅ | ✅ |
| `stock_name` | ❌ 不在响应 | ❌ 不在表（需 JOIN） | `string` ✅ | ❌ 阻塞（B1a 需 JOIN stocks） |
| `market` | ❌ 不在响应 | ❌ 不在表（需 JOIN） | `string` ✅ | ❌ 阻塞（B1a 需 JOIN stocks） |
| `industry` | ❌ 不在响应 | ❌ 不在表（需 JOIN） | `string?` | ❌ 阻塞（B1a 需 JOIN stocks） |
| `focus_reason` | `string?` ✅ | `string?` ✅ | `string?` ✅ | ✅ |
| `added_at` / `created_at` | `created_at`（datetime） | `created_at`（datetime） | `added_at`（string） | ⚠️ 可映射解决 |
| `user_id` | `int` ✅（不返回前端） | `int` ✅ | 不需要 | ✅ |

> ⚠️ 标记项：需在 B1a 中解决后才能进行 B1b 前端切换。

---

## 已知差异

### 1. ID 类型冲突（高优先级）
- 后端：`id: int`，路由参数 `{item_id}` 也是 `int`
- 前端：`id: string`（当前 localStorage 写入用 `watch_${Date.now()}` 生成）
- 前端切换后需将 `id` 从 `string` 改为 `number`，PUT/DELETE 路由参数从 `string` 改 `number`

### 2. 股票基本信息缺失（中优先级）
- 当前 API 响应只含 `id`、`user_id`、`stock_id`、`focus_reason`、`created_at`、`updated_at`
- 前端 `WatchlistItem` 期望的 `stock_name`、`market`、`industry` 不在响应中
- `WatchlistItemWithStock` schema 存在但 API 未返回
- 前端展示层（WatchlistPage、HomePage）依赖 `stock_name`、`market`，切 API 后会显示为空

### 3. `added_at` 字段名差异（低优先级）
- 后端用 `created_at`
- 前端用 `added_at`
- 切换后可统一用 `created_at`，前端做一次映射

### 4. 两套表并存（架构风险）
- 当前 API 绑定旧表 `watchlist_items_legacy`（int ID）
- v2 表 `watchlists`（UUID）有更完整字段，但 API 未接入
- 若 B1 直接接入当前 API，等于在旧表上构建功能，后续迁移成本高

---

## 建议

### 方案 A：接入现有 API + 补字段（短期）

**前提**：接受 API 绑定 `watchlist_items_legacy`，不迁移到 v2 表

1. 前端 `WatchlistItem.id` 改为 `number`
2. 后端 API 响应补充 `stock_name`、`market`、`industry`（JOIN stocks 表），或前端单独调 `/api/v1/stocks/{stock_id}` 获取
3. 前端 `added_at` 映射为 `created_at`
4. 清理 `utils.ts` localStorage helpers

**优点**：改动小，立即可用
**缺点**：绑定旧表，UUID v2 迁移需另做

### 方案 B：API 升级 + 接入 v2 表（中期，推荐）

1. 新增/改造 `GET /api/v1/watchlist`，返回 `WatchlistItemWithStock`（JOIN stocks 表，填充 stock_name/market/industry）
2. 新增/改造 `POST /api/v1/watchlist`，写入 `watchlists` v2 表（UUID ID），同时保留向后兼容
3. 前端 `WatchlistItem.id` 改为 `string`（UUID），`added_at` = `created_at`
4. 清理 localStorage

**优点**：与 v2 表对齐，无需二次迁移
**缺点**：需要后端改动，比方案 A 多一轮

---

## 下一步建议

B0 结论：**前提**部分满足，建议走**方案 B**（API 升级 + 接入 v2 表），不做方案 A 的"接入旧 API 绑定旧表"。

理由：观察池异动提醒（P2）需要 `watchlists` v2 表的 `notify_on_events` 等字段，在旧表上构建功能，后续迁移成本高于当前改造成本。

建议在 B1 之前加一个 `B1a: watchlist API 升级至 v2 表` 任务，输出：补齐 v2 表的 list/add/remove 接口、JOIN stocks 返回股票基本信息、id 改为 UUID。
