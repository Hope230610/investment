# Watchlist 契约核查 — 设计文档

## 核查范围（实际执行）

### 1. 后端路由核查 ✅

文件：`investment-back/src/api/v1/watchlist.py`

已确认四条路由均可用，依赖 `get_current_user` 鉴权，user_id 隔离正确。

### 2. 数据模型核查 ✅

发现**两套表并存**：
- `watchlist_items_legacy`（Integer ID）— 当前 API 实际读写此表
- `watchlists`（UUID ID）— v2 设计，API 未接入，但有更丰富字段

### 3. 字段映射核查 ✅

发现三处关键差异：
1. `id` 类型：后端 `int` vs 前端 `string`
2. 股票基本信息：后端响应缺 `stock_name/market/industry`，前端展示层依赖这些字段
3. 时间字段名：`added_at` vs `created_at`

### 4. API vs v2 表对齐 ✅

当前 API 绑定旧表（`watchlist_items_legacy`），不满足 v2 路线图前提。

## audit-report.md 内容结构

```
# 后端路由现状（表）
# 数据模型现状：两套表并存（表）
# 字段映射表（表）
# 已知差异（1-4）
# 建议（方案 A vs 方案 B）
# 下一步建议
```

## conclusion.md 内容结构

```
# B1 前提确认
## 结论：前提不满足
## 详细说明（3条结构性缺陷）
## 推荐路线图（B0 → B1a → B1b → B2）
## B1 能否"先上车后补票"？→ 不建议
## B0 核查产出清单（表）
```

## 实际发现摘要

| 核查项 | 结果 |
|--------|------|
| 后端 watchlist 路由是否完整 | ✅ GET/POST/PUT/DELETE 均存在 |
| 权限隔离是否正确 | ✅ 全部依赖 `get_current_user` + user_id filter |
| ID 类型是否与前端一致 | ❌ 后端 int，前端 string |
| 响应字段是否完整 | ❌ 缺 stock_name/market/industry |
| 是否绑定 v2 表 | ❌ 绑定 `watchlist_items_legacy`（旧表） |
| 是否有 pagination | ❌ 无，预计用户量级下暂不需要 |
