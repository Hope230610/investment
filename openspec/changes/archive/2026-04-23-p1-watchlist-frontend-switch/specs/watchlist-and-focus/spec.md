# watchlist-and-focus: 前端服务端化切换（B1b 实施记录）

## Purpose

本 spec 是 `p1-watchlist-frontend-switch` 变更的实施记录，对齐 `watchlist-and-focus` baseline spec § Requirement 1（观察列表必须按用户持久化），确认 B1a 冻结的 v2 API 契约已在前端全链路落地。

## Implementation Summary

### What Changed

| 文件 | 变更 |
|------|------|
| `WatchlistPage.tsx` | list → `getWatchlistItems()`；delete → `deleteWatchlistItem()`；`created_at` 展示；乐观删除 + 失败回滚 + Toast |
| `HomePage.tsx` | list → `getWatchlistItems()` from `api.ts` |
| `ResultPage.tsx` | add → `postWatchlistItem()`；delete → `deleteWatchlistItem()`；"已在列表"判断 → `getWatchlistItems()` 响应；捕获 API 返回 `id` 供删除使用 |
| `StockSearchPage.tsx` | add → `postWatchlistItem()`；"已添加"判断 → `getWatchlistItems()` 响应；`Set<string>` 存储 stock_id |
| `utils.ts` | 移除 `getWatchlist` / `addToWatchlist` / `removeFromWatchlist`；保留 `getFocusReasons` / `addFocusReason` |
| `types.ts` | `WatchlistItem` / `WatchlistApiItem` 注释更新为 B1b 完成状态 |

### Alignment with Baseline Spec

**Baseline § Requirement 1 要求**：观察列表必须按用户持久化，不再依赖单设备本地状态。

B1b 完成后：
- ✅ 用户在任意设备登录后看到同一份服务端观察列表
- ✅ 读写受资源归属鉴权保护（API 层 `get_current_user`）
- ✅ `postWatchlistItem` 实现 idempotent upsert（`user_id + stock_id` 不重复）
- ✅ `record-reason` 与 watchlist 专用 API 共用 `watchlists` v2 数据源

### Breaking Changes

| 破坏点 | 说明 |
|--------|------|
| `WatchlistItem.id` 不再使用 | 页面层改用 `WatchlistApiItem`，id 为 UUID |
| localStorage `ai_investment_watchlist` 不再写入 | 旧数据不再被读取；新数据写入服务端 |
| `WatchlistItem.added_at` 不再从 localStorage 生成 | 展示改为 `created_at` 映射 |

### Pending

- 手动 smoke 6 项（见 tasks.md 3.2）
