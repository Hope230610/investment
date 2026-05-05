# P3 Online Release Acceptance

## 1. 本次 P3 实现范围

- 复盘成长引擎：新增 `GrowthService`，将历史复盘、判断质量、情绪记录和行为干预聚合为 caution context，并注入分析创建与 worker。
- AI 评测系统：新增 `AiEvalService` 和测试，覆盖合规表达、结构完整性、不确定性、输出标记和持仓上下文来源。
- 分享型结构化卡片：新增分享快照模型、服务、API、ResultPage 入口和公开分享页。
- 初步商业化能力：新增 free/pro plan、usage counter、daily analysis/share card limit。
- Prompt / 模板版本化：结果 metadata 新增 template/provider/model/schema/generated/data snapshot 字段。

## 2. 未做范围

- 未接入真实支付。
- 未实现图片海报导出。
- 未做 AI eval 管理后台 UI。
- 未改变 P2 portfolio 的核心数据录入边界。

## 3. 数据库迁移

- 新增 `013_add_p3_release_tables.py`。
- 新增表：`share_snapshots`、`user_entitlements`、`usage_counters`。
- 新增 enum：`plancodeenum`、`shareprivacylevelenum`。

## 4. 后端改动

- 新增 `src/models/p3.py`、`src/schemas/p3.py`。
- 新增服务：`ai_eval_service.py`、`growth_service.py`、`share_service.py`、`entitlement_service.py`。
- 新增 API：`src/api/v1/p3.py`。
- `analysis.py` 与 `workers/tasks.py` 注入服务端成长上下文和 usage limit。

## 5. 前端改动

- `ResultPage` 增加分享按钮。
- 新增 `SharePage`。
- `api.ts` 增加分享快照创建、公开读取、撤销 helper。
- `types.ts` 增加分享卡片类型。

## 6. AI / Prompt 改动

- 分析结果 detail metadata 记录 prompt template、provider/model、schema version、generated_at 和 data_snapshot_timestamp。
- 分享卡片使用 sanitizer 和 AI eval 双重检查。

## 7. 合规边界

- `OutputQualityService` 与 `AiEvalService` 均阻断明确荐股、喊单、收益承诺和自动交易表达；本轮补充了常见英文直给与收益承诺表达覆盖。
- 分享卡片声明“仅用于风险教育和决策过程，不构成投资建议”。
- 分享卡片标题、摘要和列表字段均经过交易表达 sanitizer 与敏感 key 脱敏；公开接口不返回私有归属字段。
- 成长引擎只输出复盘偏差、自检规则和降低置信度提示。

## 8. 安全与用户隔离

- 分析读取仍按 `AnalysisTask.user_id` 过滤。
- 分享创建只允许当前用户分享自己的分析。
- 分享公开读取不返回 user_id、source_id、持仓数量、成本价、盈亏、交易流水。
- usage counter 以 `user_id + usage_key + usage_date` 唯一隔离。

## 9. 测试命令

本轮 P3 RC Hardening 实际执行命令见下方“测试结果”。所有结果均来自本地工作区，不包含正式生产环境验证。

## 10. 测试结果

- `python -m py_compile src/models/p3.py src/schemas/p3.py src/services/ai_eval_service.py src/services/growth_service.py src/services/share_service.py src/services/entitlement_service.py src/api/v1/p3.py src/services/output_quality_service.py src/api/v1/analysis.py src/workers/tasks.py src/services/analysis_generation_service.py`：通过。
- `python -m py_compile alembic/versions/012_add_portfolio_tables.py alembic/versions/013_add_p3_release_tables.py`：通过。
- `pytest -q`：109 passed，130 warnings。
- `pytest tests/test_p2_portfolio_isolation.py`：已随全量 pytest 和 P3/P2 定向回归通过。
- `pytest tests/test_portfolio_service.py`：已随全量 pytest 和 P2 定向回归通过。
- `pytest tests/test_notification_service.py -q`：15 passed。
- `pytest tests/test_ai_eval_service.py tests/test_growth_service.py tests/test_entitlement_service.py tests/test_share_service.py -q`：历史记录为 15 passed。
- `pytest tests/test_ai_eval_service.py tests/test_growth_service.py tests/test_entitlement_service.py tests/test_share_service.py tests/test_p2_portfolio_isolation.py -q`：30 passed。
- `pytest tests/test_ai_eval_service.py tests/test_share_service.py tests/test_output_quality_service.py -q`：18 passed，覆盖本轮英文合规词与分享标题/摘要脱敏补丁。
- `pytest tests/test_learning_feedback_api.py -q`：在 `investment_test` 专用库、`RUN_DATA_MODIFYING_TESTS=true` 下通过，11 passed；未绕过测试守卫。
- `alembic current`：013 (head)。
- `alembic upgrade head`：通过。首次执行时发现本地库存在 P2/P3 表但 Alembic version 停在 011，已将 012/013 收口为幂等迁移后升级到 head。
- `alembic upgrade head --sql`：通过生成 SQL。
- throwaway `investment_migration_test`：从当前模型 schema `alembic stamp head` 后执行 `alembic downgrade 011 && alembic upgrade head`，012/013 往返通过，最终 `013 (head)`。
- throwaway 空库全链路 `alembic upgrade head`：未通过，卡在历史迁移 `002` 的 `interactionscenario` enum 重复创建；该问题不是 012/013 新增，但说明“从空库 replay 全链路迁移”尚不能作为上线验收通过项。
- `npm run lint`：通过。
- `npm run test`：3 files passed，52 tests passed。
- `npm run build`：通过，Vite 提示主 chunk 543.77 kB 超过 500 kB。
- `npm run test:e2e -- --list`：列出 22 个 Playwright 用例。
- `npx playwright test tests/e2e/portfolio.spec.ts --workers=1 --trace on`：1 passed。
- `npx playwright test tests/e2e/analysis-pipeline.spec.ts --workers=1`：4 passed。
- `npx playwright test tests/e2e/decision-card-evidence.spec.ts --workers=1`：首次失败于 strict locator；修复后 7 passed。
- `npx playwright test tests/e2e/learning-feedback.spec.ts --workers=1`：5 passed。
- `npx playwright test tests/e2e/learning-feedback-personalization.spec.ts --workers=1`：fresh `investment_e2e` 上 5 passed。
- `npm run test:e2e`：fresh `investment_e2e` 上 22 passed，耗时约 8.4 分钟。

## 11. 未跑测试与原因

- 生产库 Alembic downgrade/upgrade：未执行，避免删除真实 P2/P3 表；只在 throwaway DB 验证 012/013 往返。
- Playwright 240s / 300s 外层超时：已定位。完整 22 个用例本地实际耗时约 8.4 分钟；此外重复调试未重置 `investment_e2e` 时会消耗 `daily_analysis` usage，页面停在 `daily_analysis 已达到当前方案限制`，表现为等待 `/result` 超时。
- Redis/RQ 非默认路径：本轮仍未做生产拓扑验证；默认 E2E 覆盖的是开发/测试路径。

## 12. 已知限制

- Redis/RQ、真实行情服务和真实 PostgreSQL 可用性取决于运行环境。
- 当前价格/行情快照不是实时交易级行情，不应表达为实时交易依据。
- AI eval 目前是确定性规则，样例覆盖仍不足，需要继续扩充中英文违规表达、边界表达和真实模型输出样本。
- 支付未接入，商业化能力是权限与用量边界，不代表真实收费闭环。
- `PLAN_LIMITS` 是工程边界和上线前商业化预留，不代表完整付费系统。
- Vite build 仍有主 chunk 超 500 kB warning，未在本轮拆包。
- 012/013 迁移包含 `_table_exists/_index_exists` 幂等兼容逻辑，用于收口本地“表已存在但 alembic version 停在 011”的脏库；这不应被视为生产迁移策略。生产/预发应以确定性迁移和迁移前 schema 检查为准。

## 13. 上线前仍需人工确认项

- 合规人员 review 分享卡片文案、免责声明和 sanitizer 规则。
- 产品确认 free/pro limits 数值。
- 运维确认 DB migration 在预发环境的 upgrade/downgrade，并决定是否移除或保留 012/013 的本地脏库兼容逻辑。
- 真实行情服务与 RQ worker 在部署环境可用。
- 确认 CI E2E 外层超时大于完整套件真实耗时，且每次 E2E 前重置 dedicated test DB usage counters。

## 14. 回滚策略

- 禁用 `/api/v1/p3/*` 路由和前端分享入口。
- 保留 P3 表不影响主流程；必要时执行 `013` downgrade。
- 若 usage limit 误伤，临时调宽 `PLAN_LIMITS` 或关闭创建分析前的 entitlement check。

## 15. 是否可以进入 release candidate

可以进入 P3 release candidate review，但暂不建议直接上线。原因：P2/P3 核心后端、前端、专用 test DB、Playwright full E2E 和 012/013 throwaway 往返均已通过；但仍存在合规人工 review、AI eval 样例不足、Redis/RQ 生产拓扑未验、真实支付未接入、当前价格非实时、Vite chunk warning、历史空库迁移 replay 失败，以及 012/013 幂等逻辑是否适合正式迁移策略的 review 风险。

## 16. P3 RC Review Pack Update - 2026-05-05

- Current state: P3 release candidate review candidate. This is not a formal online/production-ready state.
- Empty database migration chain: fixed and verified on throwaway `investment_rc_empty`; `alembic upgrade head` now reaches `013 (head)`.
- 012/013 migration strategy review: `_table_exists/_index_exists` is retained only as a local dirty-db compatibility guard. It is not the preferred long-term production migration strategy. To reduce silent skip risk, existing tables now require key-column schema assertions before the migration can continue; missing fields fail fast instead of being silently accepted. Formal pre-prod/prod rollout should still use deterministic migrations plus a pre-migration schema check.
- 012/013 downgrade/upgrade path: verified on throwaway `investment_rc_cycle` with `alembic upgrade head`, `alembic downgrade 011`, `alembic upgrade head`, final `013 (head)`.
- E2E baseline: fresh `investment_e2e` previous full run was `22 passed`, about 8.4 minutes; this RC review pack rerun was `22 passed` in 7.3 minutes. Playwright now has a 12-minute `globalTimeout`; CI should still allocate a margin above this and should not reuse a stale usage-limited DB.
- E2E data requirement: run `python scripts/prepare_e2e_db.py --username testuser --password testpassword123` before full E2E to rebuild the dedicated test schema, seed stocks/user/profile, reset analysis history, and reset `daily_analysis` / share usage counters. `--skip-reset` is only for narrow local debugging.
- Frontend build caveat: `npm run build` previously passed with Vite main chunk warning, `543.77 kB > 500 kB`; bundle splitting remains a later hardening item.
- Manual review still required before release: share compliance copy and disclaimer wording; sanitizer coverage for title/summary/list fields; AI eval sample coverage, especially bilingual unsafe phrasing and real model outputs; free/pro commercial limits and true payment integration; Redis/RQ production topology; real market-data availability and timestamp wording.
- Current price caveat: displayed/used prices are not real-time trading-grade quotes and must not be described as real-time trading advice.
- Release checklist before formal launch: pre-prod full migration replay; production backup/rollback rehearsal; dedicated fresh E2E DB run; Redis/RQ worker verification; payment-provider integration decision; compliance approval; AI eval sample expansion; Vite chunk follow-up or accepted risk sign-off.

## 17. Final Pre-Submit Closure - 2026-05-05

- P2/P3 focused backend tests: 36 passed.
- Backend full `pytest`: 113 passed.
- Alembic current: 013 head.
- Alembic upgrade head: success / no-op.
- Frontend tests: 52 passed.
- Frontend build: passed, with only the existing Vite chunk-size warning.
- MockMarket full acceptance: 22 passed.
- `need.md`: unchanged.
- Compliance grep: no real user-visible stock recommendation, trading-call, or return-promise wording found outside expected docs/tests/guard word lists.
- Scope status: RC is ready for split commit review; this is not formal production launch, does not connect real payment, and does not connect a real LLM.
