## Why

`watchlist-contract-audit` 已确认当前 `/api/v1/watchlist` 虽然可用，但仍绑定 `watchlist_items_legacy`，且返回字段无法满足前端展示与后续提醒能力，导致 B1 前端切换前提不成立。现在需要先把观察列表 API 升级到 `watchlists` v2 与统一契约口径，否则我们会继续在错误的数据源和错误的 ID 体系上追加开发。

## What Changes

- 将 `/api/v1/watchlist` 从 legacy 表读写迁移到 `watchlists` v2，统一以 UUID 作为观察项标识。
- **BREAKING** 调整观察列表 API 响应契约：列表与写接口返回可直接供前端展示的字段集合，补齐 `stock_name`、`market`、`industry`，并统一时间字段语义。
- 保留 `POST /api/v1/analysis/{id}/record-reason` 与观察列表的幂等联动，确保 `user_id + stock_id` 不产生双写分裂。
- 明确 legacy watchlist 路径的退役策略，避免继续向 `watchlist_items_legacy` 写入新数据。
- 为 B1b 前端切换提供冻结后的 API 契约、迁移约束与验收清单。

## Capabilities

### New Capabilities

无

### Modified Capabilities

- `watchlist-and-focus`: 将观察列表的专用 API 读写路径收口到 `watchlists` v2，并要求返回完整展示字段与 UUID 契约，替代当前 legacy `/api/v1/watchlist` 行为。

## Impact

- 关联基线文档：
  - `structure/database_design.md`
  - `structure/investment_api_contract_and_implementation_alignment.md`
  - `structure/investment_current_implementation_gap_audit.md`
  - `structure/investment_team_execution_board.md`
- 受影响执行板泳道：
  - 后端负责人 `TASK-BE-101 观察列表与关注理由服务端闭环`
  - 前端负责人 `TASK-FE-101 观察列表改为服务端优先`
- 预计受影响代码区域：
  - 后端：`investment-back/src/api/v1/watchlist.py`、`investment-back/src/services/watchlist_service.py`、`investment-back/src/models/watchlist_v2.py`、`investment-back/src/schemas/watchlist.py`
  - 数据库：`investment-back/alembic/versions/*watchlist*` 与 `watchlists` 相关约束、索引、枚举一致性
  - 前端后续依赖面：`investment-front/src/types.ts`、观察列表相关页面与 API 调用层将在 B1b 消费本次契约
