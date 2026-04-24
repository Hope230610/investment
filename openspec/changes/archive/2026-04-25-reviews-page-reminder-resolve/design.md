## Why

smoke 发现 ReviewsPage 入口走完后未完成 reminder 数量未减少。根因是 ReviewsPage 入口创建新 analysis 时，后端在两个位置都会创建新 ReviewTask，抵消了 patch 原始 reminder 的效果。

## What Changes

### 1. PostTradeInput.tsx — 透传 pendingReviewTaskId

在 `POST /api/v1/analysis` 请求体的 `scenario_payload` 中加入 `pending_review_task_id`：

```typescript
// investment-front/src/pages/PostTradeInput.tsx:63
scenario_payload: {
  // ... 原有字段 ...
  pending_review_task_id: pendingReviewTaskId || undefined,
}
```

`pendingReviewTaskId` 来自 URL search param（`pending_review_task_id`，来自 ReviewsPage 链接）或空字符串（直接入口）。

### 2. analysis_service.py — 创建时跳过

```python
# investment-back/src/services/analysis_service.py:120-122
scenario_payload = analysis_data.scenario_payload or {}
skip_review_task = scenario_payload.get("pending_review_task_id")
if analysis_data.scenario.value == "post_trade_review" and not skip_review_task:
    # ... 原有创建 ReviewTask 逻辑 ...
```

### 3. analysis.py — completion 时跳过

```python
# investment-back/src/api/v1/analysis.py:388-391
scenario_str = task.scenario.value if hasattr(task.scenario, "value") else task.scenario
should_skip_review_task = (
    scenario_str == "post_trade_review"
    and scenario_payload.get("pending_review_task_id")
)
if review_at and not should_skip_review_task:
    # ... 原有创建/更新 ReviewTask 逻辑 ...
else:
    logger.info("review_task_skipped_by_pending_resolution", task_id=str(task.id))
```

## Data Flow

```
ReviewsPage "去复盘" 链接
  ?stock_id=SZ000001&stock_name=XXX&pending_review_task_id=<旧analysis UUID>

PostTradeInput.tsx
  read pendingReviewTaskId from URL param
  POST /api/v1/analysis
    scenario_payload.pending_review_task_id = "<旧analysis UUID>"
    ↓
analysis_service.py
  create_analysis_task()
    skip_review_task = scenario_payload.get("pending_review_task_id")  # True
    → 不创建 ReviewTask
    ↓
process_analysis_v2 (background)
  should_skip_review_task = True
  → 不创建 ReviewTask
  ↓
ResultPage.tsx
  patchReviewResult(pendingReviewTaskId, {mark_completed: true})
  → 原始 reminder status = COMPLETED
  ↓
未完成数：29 → 28
```

## Backwards Compatibility

- 直接入口（无 `pending_review_task_id`）：`scenario_payload` 中无此 key，两处 `skip_review_task = None`，条件为 False，走原有创建路径
- 所有现有 API 契约不变（无新增字段、无新增路由）
