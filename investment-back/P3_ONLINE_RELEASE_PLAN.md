# P3 Online Release Candidate Plan

## 1. P3 上线候选目标

P3 目标是把 AI 投资决策助手从 P0/P1/P2 的“可用闭环”推进到可上线候选版：用户可以持续记录判断，系统可以把历史复盘转化为下一次分析的结构化 caution context，AI 输出有确定性评测守卫，分享卡片经过脱敏与合规处理，商业化边界有 plan / entitlement / usage limit 的基础表达。

## 2. 本次实现范围

- 新增 `GrowthService`，聚合 review / judgment / emotion / intervention 历史，生成结构化 caution context。
- 单股分析和 worker 任务重建服务端 `holding_context` 后注入 `growth_caution_context`。
- 新增 `AiEvalService`，覆盖合规表达、结构完整性、不确定性、输出标记和持仓上下文来源检查。
- 新增 `ShareSnapshot` 分享快照模型、API 和前端公开分享页，默认不暴露 user_id、source_id、持仓数量、成本价、盈亏和交易流水。
- 新增 `UserEntitlement` / `UsageCounter`，支持 free / pro plan、每日分析次数和分享卡片次数限制。
- 扩展 prompt / 模板版本元数据，结果持久化记录 template id/version、provider、model、output schema、生成时间和数据快照时间。

## 3. 明确不做范围

- 不接入真实支付，不伪造订阅成功。
- 不提供自动交易、自动调仓、荐股海报、收益承诺或目标收益功能。
- 不做复杂 AI eval UI；P3 只提供后端服务、API 和固定测试样例。
- 不把完整敏感 prompt、API key 或系统密钥暴露到前端。

## 4. 数据结构影响

新增迁移 `013_add_p3_release_tables.py`：

- `share_snapshots`
- `user_entitlements`
- `usage_counters`
- enum `plancodeenum`
- enum `shareprivacylevelenum`

不修改 P0/P1/P2 既有表结构；P2 的 `012_add_portfolio_tables.py` 仍作为 P3 迁移前置。

## 5. 后端影响

- 新增 P3 API：`/api/v1/p3/growth/caution-context`、`/api/v1/p3/ai-eval`、`/api/v1/p3/entitlements`、`/api/v1/p3/shares`、`/api/v1/p3/public/shares/{share_id}`。
- `POST /api/v1/analysis` 会执行 daily analysis usage limit，并注入服务端成长上下文。
- worker 会重新生成服务端持仓上下文和成长上下文，避免客户端伪造字段进入结果。

## 6. 前端影响

- ResultPage 增加分享卡片按钮。
- 新增 `/share/:shareId` 公开分享页，展示结构化证据、风险、失效条件和免责声明。
- 分享页不需要登录，不展示用户 id、内部 source id、持仓数量、成本价、盈亏和交易流水。

## 7. AI / Prompt 影响

- 分析结果 metadata 记录 `prompt_template_id`、`prompt_template_version`、`model_provider`、`model_name`、`generated_at`、`output_schema_version`、`data_snapshot_timestamp`。
- 当前 provider 为 `rules_engine` / `deterministic-v1`，为后续真实 LLM provider 留出追踪字段。
- AI eval 以确定性规则作为上线守卫，不替代人工合规 review。

## 8. 合规边界

- 禁止输出建议买入、建议卖出、重仓、稳赚、明天会涨、目标收益、跟着买、抄底机会、强烈推荐、自动调仓、自动交易等表达。
- 分享内容经过 sanitizer 和 eval 检查，只保留风险教育、决策过程、证据结构。
- 成长引擎只提示历史偏差、自检问题、冷静期和降低置信度条件，不输出交易指令。

## 9. 测试计划

- 后端：新增 `test_ai_eval_service.py`、`test_growth_service.py`、`test_entitlement_service.py`、`test_share_service.py`。
- 回归：P2 portfolio isolation/service、notification、learning feedback、analysis contract、output quality。
- 数据库：`alembic current`、`alembic upgrade head`，如环境允许执行 downgrade/upgrade 往返。
- 前端：`npm run lint`、`npm run test`、`npm run build`，必要时执行 Playwright。

## 10. 验收标准

- P3 服务测试通过，P0/P1/P2 关键测试不回退。
- 分享快照无法访问他人分析，公开读取不暴露敏感字段，撤销/过期后不可访问。
- AI eval 能阻断荐股表达、缺失反方证据、缺失失效条件、过度确定性表达和客户端持仓上下文。
- free plan 超限返回统一错误，pro plan 放宽限制，usage 跨用户隔离。

## 11. 已知限制

- 未接入真实支付和订阅网关。
- AI eval 样例集仍是确定性规则集，不能覆盖所有自然语言变体。
- 分享卡片是文本结构化页面，不是图片导出海报。
- 行情数据实时性仍依赖现有 market data service。

## 12. 回滚策略

- 后端可先下线 `/api/v1/p3/*` 路由，保留数据库表不影响 P0/P1/P2。
- 若分享快照出现合规风险，可禁用 ResultPage 分享按钮并拒绝 `POST /p3/shares`。
- 若 entitlement 限制误伤，可临时将 plan limit 调宽或关闭 `daily_analysis` 检查。
- 数据库回滚可按 `013` downgrade 删除 P3 表；不会删除 P0/P1/P2 核心数据。
