## 1. Contract

- [x] 1.1 收口 `investment-back/src/schemas/watchlist.py` 的 v2 请求/响应 schema，定义 UUID 标识、股票摘要字段与统一时间字段语义
- [x] 1.2 统一 `/api/v1/watchlist` 的错误响应与状态码约定，使其与现有 `api_error` 契约一致并可供 B1b 联调

## 2. Backend/Data

- [x] 2.1 重构 `investment-back/src/services/watchlist_service.py`，以 `watchlists` + `stocks` 为真源实现 list/upsert/update/delete
- [x] 2.2 改造 `investment-back/src/api/v1/watchlist.py`，切换到 v2 service、UUID 参数和完整展示字段响应
- [x] 2.3 改造 `investment-back/src/api/v1/analysis.py` 的 UUID `record-reason` 路径，复用共享 watchlist service，避免双实现
- [x] 2.4 核查 `investment-back/alembic/versions/*watchlist*` 与 `watchlists` 当前模型/枚举是否一致；若不足以支撑新契约，补最小迁移

## 3. Frontend

- [x] 3.1 在 `investment-front/src/types.ts` 中补齐面向服务端 watchlist v2 的消费类型或映射约定，但不提前切换页面调用
- [x] 3.2 为后续 B1b 预留 `created_at -> added_at`、UUID 删除/更新等对接约束，避免前端继续依赖 legacy `int` 契约

## 4. QA/Release

- [x] 4.1 为 watchlist v2 主链路补最小验证：list/add/update/delete 与 `record-reason` 共用数据源的测试或可重复 smoke
- [x] 4.2 执行一轮手工联调检查，确认 `/api/v1/watchlist` 不再向 `watchlist_items_legacy` 写入新数据
- [x] 4.3 输出 B1b 接手清单：冻结后的字段契约、已知 breaking 点、回滚注意事项
