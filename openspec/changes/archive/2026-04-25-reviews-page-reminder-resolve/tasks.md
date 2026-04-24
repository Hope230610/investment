## 1. 代码实现

- [x] 1.1 PostTradeInput.tsx：在 `scenario_payload` 中透传 `pending_review_task_id`
- [x] 1.2 analysis_service.py：`create_analysis_task` 检测 `pending_review_task_id`，有值则跳过同步创建 ReviewTask
- [x] 1.3 analysis.py：`process_analysis_v2` 检测 `pending_review_task_id`，有值则跳过创建 ReviewTask，加日志 `review_task_skipped_by_pending_resolution`

## 2. Smoke 验证

- [x] 2.1 基线：DB 查询 user_id=1 未完成 reminder 数量 = 29
- [x] 2.2 ReviewsPage 入口：
      - 选一条 `post_trade_review` + 有 `analysis_task_id` 的 PENDING reminder 作为入口
      - POST `/api/v1/analysis`（带 `scenario_payload.pending_review_task_id`）
      - 轮询等待 analysis 状态变为 ready
      - 验证：新 analysis 对应的 ReviewTask **未创建**
      - PATCH `/api/v1/reviews/by-analysis/{pending_review_task_id}` 标记原始 reminder 完成
      - 验证：DB 中 reminder status = COMPLETED
      - 验证：DB 查询未完成总数 = 28
- [x] 2.3 直接入口回归：
      - POST `/api/v1/analysis`（不带 `pending_review_task_id`）
      - 验证：analysis 对应的 ReviewTask 正常创建
- [x] 2.4 清理测试数据，恢复基线 29

## 3. 代码变更记录

| 文件 | 行 | 变更 |
|---|---|---|
| `PostTradeInput.tsx` | 63 | `scenario_payload` 加 `pending_review_task_id: pendingReviewTaskId \|\| undefined` |
| `analysis_service.py` | 120-122 | `scenario_payload.get("pending_review_task_id")` 检测 + 跳过创建 |
| `analysis.py` | 388-391 | `should_skip_review_task` 条件判断 + `else` 日志分支 |
