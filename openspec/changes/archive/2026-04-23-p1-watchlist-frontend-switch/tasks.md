## 1. Contract

- [x] 1.1 补充 `p1-watchlist-frontend-switch` delta spec（`specs/watchlist-and-focus/spec.md`）：覆盖 API 切换范围、baseline 对齐状态、breaking changes

## 2. Frontend

- [x] 2.1 `WatchlistPage.tsx`：切换 list 为 `getWatchlistItems()` API，`added_at` 展示改为 `created_at`；删除改为 `deleteWatchlistItem()` API（乐观更新 + 失败回滚 + Toast）
- [x] 2.2 `HomePage.tsx`：观察列表切换为 `getWatchlistItems()` API（来自 `api.ts`）；API 失败时静默降级为空数组
- [x] 2.3 `ResultPage.tsx`：`addToWatchlist` 替换为 `postWatchlistItem()`；`getWatchlist()` 替换为 `getWatchlistItems()`；移除 `utils.ts` 的 `addToWatchlist` 和 `getWatchlist` 引用；新增 `handleRemoveFromWatchlist()` + `watchlistItemId` state；Star 按钮与底部按钮均支持加入/移除切换；`postWatchlistItem` 返回值捕获 `id` 避免重复拉取
- [x] 2.4 `StockSearchPage.tsx`：`addToWatchlist` 替换为 `postWatchlistItem()`；"已添加"判断改为基于 `getWatchlistItems()` 响应（`Set<string>`）；移除 `utils.ts` 的 `addToWatchlist` 和 `getWatchlist` 引用
- [x] 2.5 `utils.ts`：移除 `getWatchlist`、`addToWatchlist`、`removeFromWatchlist`；保留 `STORAGE_KEYS.FOCUS_REASONS` 和 `getFocusReasons`/`addFocusReason`
- [x] 2.6 `types.ts`：`WatchlistItem` + `WatchlistApiItem` 注释更新为 B1b 完成状态

## 3. QA

- [x] 3.1 TypeScript 编译零错误（app 文件）；Vite build 通过（仅 chunk size 提示，非本次引入）；vitest 46/46 全通过
- [x] 3.2 手动 smoke：
      - [x] WatchlistPage 加载时显示服务端数据
      - [x] WatchlistPage 删除后列表实时更新（乐观更新），失败时回滚
      - [x] HomePage 观察列表与 WatchlistPage 一致
      - [x] ResultPage 添加到观察列表后服务端可查到
      - [x] ResultPage 点击"移出观察列表"可正确删除（STAR 图标 + 底部按钮均可）
      - [x] StockSearchPage 添加后"已添加"状态正确
      - [x] 卸载重装后观察列表数据仍然存在（服务端持久化）
