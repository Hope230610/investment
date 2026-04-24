# B1b Handoff

## Frozen Contract

- 路径保持不变：`/api/v1/watchlist`
- `id` 已升级为 UUID 字符串
- 返回字段：
  - `id`
  - `user_id`
  - `stock_id`
  - `stock_name`
  - `market`
  - `industry`
  - `focus_reason`
  - `created_at`
  - `updated_at`

## Frontend Mapping Notes

- 现有页面本地模型 `WatchlistItem.added_at` 需要映射自 API 的 `created_at`
- 删除与更新接口都必须传 UUID 字符串，不能再传 legacy `int`
- `focus_reason` 在 API 层是 `string | null`，页面若仍沿用可选字符串，需要做 `null -> undefined` 适配

## Breaking Points

- 旧的 `int` 型 `item_id` 已失效
- 旧响应中缺失的 `stock_name` / `market` / `industry` 已成为稳定契约的一部分
- watchlist 专用 API 已不再写入 `watchlist_items_legacy`

## Rollback Notes

- 回退到旧代码不会删除 v2 数据，但会重新出现“专用 API 看不到 v2 数据”的行为回退
- 若线上启用后发现问题，优先前滚修复，不建议长期停留在 legacy 实现

## Recommended B1b Entry Points

- `investment-front/src/api.ts`
- `investment-front/src/types.ts`
- `investment-front/src/pages/HomePage.tsx`
- `investment-front/src/pages/WatchlistPage.tsx`
- `investment-front/src/pages/ResultPage.tsx`
- `investment-front/src/pages/StockSearchPage.tsx`
