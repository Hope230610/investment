## 1. Smoke 验证（Gate 0 后第一优先）

- [x] 1.1 跑通 confirm 全链路：登录 → post_trade_review → 反馈卡确认 → DB 查 emotion_history/judgment_history 有写入
- [x] 1.2 验证 Step2（PATCH /api/v1/reviews/by-analysis/{id}）：confirm 后 review_tasks.status 变为 completed（若 ReviewTask 不存在则 404，记录日志）
- [x] 1.3 验证 records/history：新表分支能返回有 headline 的记录，而非空列表
- [x] 1.4 验证 graceful degradation：分析结果未生成时，headline=None、stock_name="未知股票"正常返回
- [x] 1.5 验证 POST /api/v1/analysis/{id}/record-reason 不出现 422（验证 RecordReasonRequest schema 在 analysis.py 中正确使用）
- [x] 1.6 验证 record-reason 写入 watchlists 表后可被查询（读回路径以 GET /api/v1/analysis 或后续新实现为准）

## 2. 后端收口

- [x] 2.1 reviews.py：确认按 analysis_task_id + user_id 查 ReviewTask 的查询条件正确（smoke 过程中验证 404 根因）
- [x] 2.2 reviews.py：在 patch 路由加上结构化日志（analysis_task_id、error_code、user_id），记录 Step2 失败场景
- [x] 2.3 profile_service.py：确认 migration 008 的 unique constraint（user_id + recorded_date / user_id + judgment_date）存在
- [x] 2.4 records.py：在 new 分支返回前加 `logger.debug("records_count", count=len(records))`，确认 new 分支走到
- [x] 2.5 watchlist/v2：确认 record-reason 的 upsert 逻辑（user_id + stock_id 唯一约束），重复写入不产生脏数据

## 3. 前端收口

- [x] 3.1 ResultPage.tsx：确认读端兼容逻辑正确（读到 'confirmed' 归一化为 'true'），卡片不再因 'confirmed' 值重复弹出
- [x] 3.2 ProfilePage.tsx：验证趋势区块不静默消失（getLearningHistory 失败时至少显示空状态文案，不返回 null 导致整段不渲染）
- [x] 3.3 HomePage.tsx / RecordsPage.tsx：确认切到 /api/v1/analysis 后能正常展示记录列表（新表路径）
- [x] 3.4 LearningFeedbackCard.tsx：确认三个按钮（确认/稍后/忽略）触发的回调正确，忽略/确认均写 'true'，稍后只写 showcount（已通过 ResultPage 修复验证）

## 4. QA / Release

- [x] 4.1 补 learningFeedback.test.ts：Mock Step1 成功 Step2 失败，验证 ResultPage 行为（含静默标记 + 日志）
- [x] 4.2 补 learningFeedback.test.ts：Mock Step1 + Step2 均成功，验证 DB 落库（emotion_history + review_tasks.status）
- [x] 4.3 固化 smoke checklist 到文档（覆盖：登录、分析发起、结果页 confirm、记录页、Profile 趋势区、record-reason）
- [x] 4.4 执行一次完整 smoke 验证（单人串行，预期 1-2 小时）
- [x] 4.5 将 smoke checklist 和验证结果 commit 到仓库

---

## 已完成的代码变更（Gate 0 + 本 change）

| 文件 | 变更 |
|---|---|
| `ResultPage.tsx` | confirm/dismiss 统一写 'true'；读端兼容 'confirmed' 并归一化 |
| `profile_service.py` | upsert conflict target 改为 index_elements |
| `records.py` | new 分支三段拼接 + graceful degradation + logger.debug |
| `HomePage.tsx` / `RecordsPage.tsx` | 入口切 /api/v1/analysis |
| `analysis.py` | record-reason 从 IntegrityError 抛出改为 upsert 语义 |
| `learningFeedback.test.ts` | 新增 ResultPage confirm/dismiss localStorage 语义测试 8 条 |
| `SMOKE_CHECKLIST.md` | 固化 6 大场景 30+ 检查项 + curl 命令 |