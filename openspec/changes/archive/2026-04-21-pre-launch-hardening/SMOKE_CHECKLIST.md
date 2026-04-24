# Smoke Checklist — pre-launch-hardening

本文档固化上线前的最小验收清单，每次部署前执行。

## 前置条件

- 后端服务运行中（`uvicorn main:app`）
- 前端服务运行中（`npm run dev`）
- 数据库已迁移到 HEAD（`alembic upgrade head`）
- 已登录一个测试账号（建议用非 test@example.com 的真实用户）

---

## 1. 登录与认证

- [ ] 未携带 token 的请求返回 401，不进入 debug 放行
- [ ] `GET /api/v1/records` 未登录时返回 401
- [ ] 登录后能正常拿到 token，后续请求携带 Authorization header

---

## 2. 分析发起与结果页

- [ ] 发起一次 single_stock_check 分析，能拿到结果
- [ ] 发起一次 post_trade_review 分析，能拿到结果
- [ ] 结果页能正确渲染分析内容（headline、scenario、status）

---

## 3. Learning Feedback 确认闭环（核心）

### 3.1 Step1 — 画像写入

- [ ] 在 post_trade_review 结果页填写复盘表单并点"确认"
- [ ] 触发后端 `POST /api/v1/user/profile/learning-feedback`
- [ ] 请求不返回 500（ProfileService upsert conflict target 已修）
- [ ] 数据库查询：`SELECT * FROM emotion_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 1;`
  - 确认有最新写入，recorded_date 为今天

### 3.2 Step2 — ReviewTask 更新

- [ ] 同一次"确认"操作触发 `PATCH /api/v1/reviews/by-analysis/{id}`
- [ ] 请求不返回 400/404/500
- [ ] 数据库查询：`SELECT status FROM review_tasks WHERE analysis_task_id = ? LIMIT 1;`
  - 确认 status 为 `completed`

### 3.3 静默失败场景验证

- [ ] 若 Step2 404（ReviewTask 不存在）：卡片仍关闭，后端日志有记录
  - 查询后端日志：`grep "REVIEW_TASK_NOT_FOUND" server.log`
- [ ] 若 Step1 500：卡片仍弹出（未静默成功）

### 3.4 卡片不再重复弹出

- [ ] 确认成功后刷新结果页，卡片不再弹出（localStorage `feedback_dismissed_${id}` = 'true'）
- [ ] 旧用户本地有 `feedback_dismissed_${id}` = 'confirmed'：读取时归一化为 'true'，卡片不再弹出

### 3.5 Profile 页趋势展示

- [ ] 打开 `/profile` 页
- [ ] 趋势区块渲染（不是整块消失）
- [ ] 有情绪趋势或"暂无情绪数据，开始复盘后将自动积累"文案
- [ ] 有判断质量趋势或"暂无判断质量记录，每次复盘后将自动积累"文案

---

## 4. 记录页 / History

- [ ] 打开 `/records` 页，不出现空列表误判（除非真的没有数据）
- [ ] 列表项包含 scenario、stock_name、created_at
- [ ] `GET /api/v1/analysis` 返回新表路径数据（后端日志有 `records_count`）
- [ ] 一条无结果的任务：`headline = null`，`stock_name = "未知股票"`（graceful degradation）

---

## 5. 关注理由（Record-Reason）

- [ ] 在 post_trade_review 结果页填写"记录关注理由"并提交
- [ ] 不出现 422（RecordReasonRequest schema 正确）
- [ ] 数据库查询：`SELECT * FROM watchlists WHERE user_id = ? ORDER BY created_at DESC LIMIT 1;`
  - 确认 focus_reason 有值
- [ ] 重复提交同一股票的 record-reason：只更新 focus_reason，不产生脏数据（幂等 upsert）

---

## 6. Watchlist Split-Brain 状态检查

- [ ] `/api/v1/watchlist` 路由存在但为废弃路径，不产生新写入
- [ ] 新的关注理由走 `POST /api/v1/analysis/{id}/record-reason`（watchlists 新表）

---

## 快速回归命令

```bash
# 1. 数据库迁移验证
alembic current
alembic upgrade head

# 2. Learning feedback 画像写入
curl -X POST http://localhost:8000/api/v1/user/profile/learning-feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"analysis_task_id":"<uuid>","tag_updates":[],"judgment_quality":"主要来自判断","emotion_level":2}'

# 3. ReviewTask 状态验证
curl -X PATCH "http://localhost:8000/api/v1/reviews/by-analysis/<uuid>" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mark_completed":true}'

# 4. records/history 新表路径
curl "http://localhost:8000/api/v1/analysis?limit=5" \
  -H "Authorization: Bearer $TOKEN"

# 5. record-reason upsert
curl -X POST "http://localhost:8000/api/v1/analysis/<uuid>/record-reason" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"stock_id":"000001","reason":"年报后建仓"}'
```

---

## 失败处理策略

| 症状 | 可能原因 | 修复 |
|---|---|---|
| learning-feedback 500 | migration 008 constraint 缺失 | `alembic upgrade head` 确认 008 已执行 |
| record-reason 422 | RecordReasonRequest schema 未更新 | 检查 analysis.py 是否使用了新 schema |
| records 返回空列表 | 路由仍在旧分支 | 确认 `ANALYSIS_ROUTING["analysis"] = "new"` |
| 卡片重复弹出 | localStorage 未写入或读取判断错误 | 检查 ResultPage.tsx 读端归一化逻辑 |
| Profile 趋势区块消失 | getLearningHistory 失败 | 检查后端 `/api/v1/user/profile/learning-history` |