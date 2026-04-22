# Smoke 验证结果 — 2026-04-22

## 执行人：张烜荣

## 结果：✅ 全部通过

## 测试环境

- 浏览器：Chrome
- 后端：`uvicorn main:app --reload`（investment-back）
- 前端：`npm run dev`（investment-front）
- 结果页路由：`/analysis/<uuid>/result`（非旧版 `/result/<uuid>`）

## 测试数据

- 测试用户：user_id=1
- 股票：平安银行（SZ000001）
- single_stock_check：`b9d0e268-72f3-4dbf-95e4-41733fd08eed`
- post_trade_review：`d1c91f3a-b484-445e-bdb2-7cbb59dc1059`

---

## 1. 登录与认证

- [x] 清空会话后访问 `/records` 跳回 `/login`
- [x] 无 token 请求 `GET /api/v1/records` 返回 401
- [x] 带 token 请求正常响应

## 2. 分析发起

- [x] single_stock_check 分析成功，结果页 `/analysis/b9d0e268.../result` 正常渲染
- [x] post_trade_review 分析成功，结果页 `/analysis/d1c91f3a.../result` 正常渲染
- [x] 结果页能正确展示 headline、scenario、status

## 3. Learning Feedback 确认闭环

### 3.1 Step1 — 画像写入

- [x] POST `/api/v1/user/profile/learning-feedback` 返回 200，无 500
- [x] DB 验证：`SELECT * FROM emotion_history ORDER BY created_at DESC LIMIT 1`
  - user_id=1, recorded_date=2026-04-22, emotion_level=3
  - analysis_task_id=d1c91f3a-b484-445e-bdb2-7cbb59dc1059
- [x] DB 验证：`SELECT * FROM judgment_history ORDER BY created_at DESC LIMIT 1`
  - user_id=1, judgment_date=2026-04-22, judgment_score=100
  - judgment_label=主要来自判断

### 3.2 Step2 — ReviewTask 更新

- [x] PATCH `/api/v1/reviews/by-analysis/d1c91f3a-b484-445e-bdb2-7cbb59dc1059` 返回 200，无 404
- [x] DB 验证：`SELECT status FROM review_tasks WHERE analysis_task_id = 'd1c91f3a...'`
  - status=COMPLETED

### 3.3 卡片不再重复弹出

- [x] 确认后刷新结果页，卡片不弹出
- [x] localStorage 验证：`feedback_dismissed_d1c91f3a... = 'true'`

### 3.4 Profile 页趋势展示

- [x] `/profile` 页"学习记录"区块正常渲染
- [x] 显示"情绪趋势（最近30天）"和"判断质量历史"区块

## 4. 记录页 / History

- [x] `/records` 页非空，显示"平安银行 / 交易后复盘 / 2026/4/22"等记录
- [x] GET `/api/v1/analysis?limit=5` 返回新表路径数据：
  - d1c91f3a... / post_trade_review / 平安银行 / ready
  - b9d0e268... / single_stock_check / 平安银行 / ready

## 5. 关注理由（Record-Reason）

- [x] 两次 POST `/api/v1/analysis/d1c91f3a.../record-reason` 均返回 200，无 422/409
- [x] DB 验证：`SELECT * FROM watchlists ORDER BY created_at DESC LIMIT 1`
  - user_id=1, stock_id=SZ000001
  - focus_reason=二季报前继续跟踪
  - added_from_scenario=post_trade_review
- [x] 去重验证：user_id=1 + stock_id=SZ000001 仅有 1 条记录（upsert 幂等）

## 6. Watchlist Split-Brain 状态

- [x] `/api/v1/watchlist` 仍返回旧表 legacy 数据
- [x] 新写入走 `/api/v1/analysis/{id}/record-reason`（watchlists v2 表）
- [x] 两表数据独立，前端无调用 legacy 路径，符合"逻辑废弃"预期

---

## 结论

本次 smoke 覆盖的核心链路全部通过：

1. **Learning feedback confirm 双写**：Step1 + Step2 均落库，DB 有写入记录
2. **卡片不再重复弹出**：localStorage 归一化生效，'true' 值阻止重复展示
3. **Records/history 读源**：新表路径正常返回数据，graceful degradation 正常
4. **Record-reason upsert**：重复提交幂等，不产生脏数据
5. **Watchlist split-brain**：已知状态，legacy 路径无新写入，符合设计预期

本 change 可归档。