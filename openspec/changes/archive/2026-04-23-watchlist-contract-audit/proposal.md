## Why

观察池异动提醒和跨端一致性都依赖服务端观察列表。本变更的任务是在创建"B1：watchlist 前端全切服务端"之前，先核查清楚后端接口的实际情况。

**当前不只是"前端没接 API"，而是 legacy 与 v2 双数据源并存**。如果不先核查清楚，后续 B1 很可能把前端接到错误数据源（legacy），与已写入 v2 的分析链路形成双主链分裂，进一步放大数据不一致。B0 的核心价值是**防止错误接线**。

## What Changes

1. 核查 `investment-back/src/api/v1/watchlist.py` 所有路由（GET/POST/PUT/DELETE）
2. 核查 `investment-back/src/models/watchlist.py` 和 `watchlist_v2.py`（发现两套表并存）
3. 核查 `investment-back/src/schemas/watchlist.py` Pydantic schema 与服务层返回
4. 核查前端 `WatchlistItem` type 与后端响应的字段映射
5. 核查分析模块中 `record-reason` 写入 `watchlists` v2 的实际服务路径，确认与 legacy watchlist API 不共享数据源

## Key Findings

**后端路由现状**：现有 watchlist 路由（GET/POST/PUT/DELETE）均存在且鉴权正确，但数据源绑定为 `watchlist_items_legacy`，未接入 `watchlists` v2。

**数据模型分裂**：legacy 表使用 Integer ID，`watchlists` v2 使用 UUID，且分析链路中的 `record-reason` 已写入 v2，形成 watchlist API 与新链路并行但不共享的数据源。

**契约差异**：后端响应缺少前端展示所需的 `stock_name`、`market`、`industry` 字段；同时后端 ID 为 int、前端当前语义为 string，无法直接作为前端服务端化切换的稳定契约。

**结论**：原 B1"watchlist 前端全切服务端"的前提不满足。推荐拆分为：
- **B1a：watchlist API 升级至 v2 表并补齐响应契约**
- **B1b：前端切换至 v2 API，移除 localStorage 依赖**

## Deliverables

```
watchlist-contract-audit/
├── audit-report.md    # 路由现状 + 两套表分析 + 字段映射 + 契约差异表 + 方案建议
├── conclusion.md      # B1 前提确认 + 推荐路线图
└── design.md          # 核查执行记录
```

## Impact

- 代码变更：零
- B1 前置依赖：需先完成 B1a（API 升级接入 v2 表）再前端切换
- **后续规划影响**：原"watchlist 前端切换"不再视为独立前端任务，而应以前后端契约修正为前置阶段