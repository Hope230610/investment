# B1 前提确认

## 结论：❌ 前提不满足

### 详细说明

当前 `/api/v1/watchlist` CRUD 路由**存在且完整**（list/add/remove/update 四条链路均可用），但存在以下结构性缺陷，无法直接作为 B1 前端切换的依据：

1. **数据模型绑定错误**
   - 当前 API 读写 `watchlist_items_legacy` 表（Integer ID）
   - 新设计的 `watchlists` v2 表（UUID ID）存在但 API 未接入
   - 直接接入当前 API = 在旧表上构建，等于和 v2 路线图冲突

2. **字段缺失影响前端展示**
   - API 响应缺少 `stock_name`、`market`、`industry`（前端展示层依赖）
   - `WatchlistItemWithStock` schema 存在但未启用

3. **ID 类型不一致**
   - 后端：`id: int`
   - 前端：`id: string`
   - 需要前端改类型，但改了之后绑定的是旧表 ID 体系

### 推荐的路线图

```
B0（当前） ✅
  └─ 结论：API 存在但不满足 v2 路线图前提

B1a（新增）：watchlist API 升级至 v2 表
  ├─ 目标：list/add/remove 写入和读取 `watchlists`（UUID）
  ├─ 返回：WatchlistItemWithStock（stock_name/market/industry）
  ├─ 输出：新的 API 契约文档
  └─ 前置：migration 确认 watchlists 表字段与代码一致

B1b（前端切换）：前端全切服务端
  ├─ 前提：B1a 完成，API 契约稳定
  ├─ 改动：WatchlistPage + HomePage + ProfilePage 切 API
  ├─ 清理：移除 utils.ts localStorage helpers
  └─ 验证：add/remove/list 主链路 smoke

B2（观察池异动提醒）：基于 v2 表构建提醒规则
  ├─ 前提：B1b 完成，watchlist 数据在服务端
  └─ 依赖：watchlists.added_from_scenario / notify_on_events 字段
```

### B1 能否"先上车后补票"？

**不建议**。理由：

- `watchlist_items_legacy` 表是旧设计，已被 `watchlists` v2 替代
- 在旧表上做前端切换，等于在错误基础上投入工程量，后续迁移成本高
- B1a 的工作量不大（后端已有 `watchlist_service` 可以复用，只是表/ID 不同），但能把路线图对齐

### B0 核查产出清单

| 核查项 | 结果 |
|--------|------|
| 后端 watchlist 路由是否完整 | ✅ GET/POST/PUT/DELETE 均存在 |
| 权限隔离是否正确 | ✅ 全部依赖 `get_current_user` + user_id filter |
| ID 类型是否与前端一致 | ❌ 后端 int，前端 string |
| 响应字段是否完整 | ❌ 缺 stock_name/market/industry |
| 是否绑定 v2 表 | ❌ 绑定 `watchlist_items_legacy`（旧表） |
| 是否有 pagination | ❌ 无，预计用户量级下暂不需要 |
