## Why

B1a（watchlist API 升级至 v2 表）已完成，`/api/v1/watchlist` 现已绑定到 `watchlists` v2，响应包含完整展示字段（`stock_name`/`market`/`industry`），ID 已升级为 UUID。API 层已就绪。

但前端仍依赖 `localStorage`，观察列表在以下四方面仍存在分裂：

- **WatchlistPage**：仍读/写 localStorage，刷新页面后数据丢失
- **HomePage**：观察列表来自 localStorage，与服务端真实数据不同步
- **ResultPage**：加入观察列表写入 localStorage，服务端查不到，无法服务后续异动提醒
- **StockSearchPage**：添加操作写入 localStorage，无法触发服务端记录

不完成此变更，B1a 的服务端化成果无法触达用户，观察池异动提醒（P2）也无从构建。

## What Changes

- `WatchlistPage.tsx`：切换 list 为 `getWatchlistItems()` API，删除为 `deleteWatchlistItem()` API，`added_at` 展示映射为 `created_at`
- `HomePage.tsx`：切换观察列表为 `getWatchlistItems()` API
- `ResultPage.tsx`：切换加入/移除观察列表为 `postWatchlistItem()` / `deleteWatchlistItem()` API；"已在观察列表"判断从 localStorage 改为 API 响应
- `StockSearchPage.tsx`：切换添加为 `postWatchlistItem()` API；"已添加"判断从 localStorage 改为 API 响应
- `utils.ts`：移除 `getWatchlist` / `addToWatchlist` / `removeFromWatchlist`，不再有 watchlist localStorage 写入路径
- `types.ts`：更新 `WatchlistItem` 注释，`added_at` 明确标注为 `created_at` 映射来源

> **不做**：修改 API 路由契约（B1a 已冻结）；修改 `watchlists` 数据模型；新增 watchlist 页面或组件

## Capabilities

### Modified Capabilities

- `watchlist-and-focus`：观察列表的读、写、删除全链路切换到服务端 API，localStorage 不再作为数据来源；用户跨设备登录后看到同一份服务端持久化列表

## Impact

- 前端影响范围：`WatchlistPage.tsx`、`HomePage.tsx`、`ResultPage.tsx`、`StockSearchPage.tsx`、`utils.ts`、`types.ts`
- 后端影响范围：无（API 契约 B1a 已冻结）
- 数据模型影响：无
- 发布影响：无 migration；上线后 localStorage 中的旧 watchlist 数据不再被读取（下次添加自动同步到服务端）
- 关联文档：B1a handoff `b1b-handoff.md`，B1a smoke `watchlist-v2-smoke.md`