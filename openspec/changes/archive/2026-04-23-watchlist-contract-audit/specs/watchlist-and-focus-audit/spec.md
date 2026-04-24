# watchlist-contract-audit: 观察列表契约核查结果

## Purpose

本 spec 是 `watchlist-contract-audit` 变更的正式审计结论，记录对观察列表服务端接口、数据模型与前端类型的核查结果。本 spec **不修改 baseline spec 行为**，仅作为审计记录存档，供后续 B1a/B1b 实施使用。

## Audit Summary

| 核查项 | 结果 |
|--------|------|
| 后端 watchlist 路由是否完整 | ✅ GET/POST/PUT/DELETE 均存在 |
| 权限隔离是否正确 | ✅ 全部依赖 `get_current_user` + user_id filter |
| ID 类型是否与前端一致 | ❌ 后端 `int`，前端 `string` |
| 响应字段是否完整 | ❌ 缺 `stock_name`/`market`/`industry` |
| 是否绑定 v2 表 | ❌ 绑定 `watchlist_items_legacy`（旧表） |
| record-reason 是否写入 v2 | ✅ 分析链路已写入 `watchlists` v2 |
| pagination | ❌ 无，预计用户量级下暂不需要 |

## Findings vs. Baseline Spec

### Finding 1: 后端 API 绑定旧表，与 spec 要求不一致（高）

**Baseline spec 规定**（`watchlist-and-focus/spec.md` § Requirement 1）：

> 观察列表的服务端真源为 `watchlists` 表（新版），不再是 `watchlist_items_legacy` 表（旧版）。`/api/v1/watchlist` 路由对应的 WatchlistService 路径为**废弃路径**，不再向前端新增调用。

**实际情况**：

`investment-back/src/api/v1/watchlist.py` 中的 GET/POST/PUT/DELETE 路由**仍然活跃**，并且读写的是 `watchlist_items_legacy` 表（Integer ID），并未接入 `watchlists` v2 表（UUID）。

这与 baseline spec 的要求存在直接冲突：spec 说废弃路径不得向前端新增调用，但后端实现仍然绑定旧表。

### Finding 2: 分析链路已写入 v2，形成双主链分裂（高）

`POST /api/v1/analysis/{id}/record-reason` 已将关注理由写入 `watchlists` v2 表（UUID）。但前端若接入当前 `/api/v1/watchlist`（legacy Integer ID），会造成：

- 通过 record-reason 添加的标的：在 legacy 表中**查不到**
- 通过 legacy API 添加的标的：在 v2 表中**查不到**

两条写入链路互不感知，数据永久分裂。

### Finding 3: 响应字段缺失影响前端展示（中）

当前 GET `/api/v1/watchlist` 响应字段：

```
{ id, user_id, stock_id, focus_reason, created_at, updated_at }
```

前端 `WatchlistItem` 展示依赖 `stock_name`、`market`、`industry`，这些字段既不在 legacy API 响应中，也不在 v2 表中（需 JOIN stocks 表）。

### Finding 4: ID 类型不一致（低）

- legacy API：`id: int`，PUT/DELETE 参数 `item_id: int`
- v2 表：`id: UUID`（string）
- 前端当前：`id: string`（`watch_${Date.now()}`）

前端切换到 v2 API 时需将 `id` 改为 string（UUID）。

## Required Actions (B1a)

以下字段修复必须在 B1b 前端切换之前完成：

1. **路由绑定迁移**：将 GET/POST/PUT/DELETE 路由的服务层从 `watchlist_items_legacy` 改为 `watchlists` v2（UUID）
2. **JOIN stocks 表**：GET 响应 JOIN stocks 表，填充 `stock_name`、`market`、`industry`
3. **UPSERT 语义**：确保 POST 写入 v2 表时实现 idempotent upsert（基于 `user_id + stock_id`）
4. **删除旧路由或限制**：正式废弃 `/api/v1/watchlist` 对 legacy 表的写入（可保留读以兼容过渡期）

## Non-Blocking Notes

以下差异可在 B1b 之后迭代解决：

- `added_at` vs `created_at` 字段名差异：前端可做一次映射
- pagination：当前用户规模下暂不需要

## Audit Metadata

- 核查时间：2026-04-22
- 核查文件：`investment-back/src/api/v1/watchlist.py`、`watchlist_service.py`；`models/watchlist.py`、`models/watchlist_v2.py`；`schemas/watchlist.py`；`investment-front/src/types.ts`、`utils.ts`
- 关联 baseline spec：`watchlist-and-focus/spec.md`
- 后续变更：B1a（API 升级至 v2 表）、B1b（前端切换）
