## Context

上一轮 smoke（2026-04-22）验证 learning feedback confirm 链时发现：`ReviewsPage` 入口走完后，首页角标未完成数从 `29` 保持为 `29`，未实现预期的净减少。

**根因链路**：

```
ReviewsPage "去复盘"
  → PostTradeInput（pendingReviewTaskId=UUID(旧analysis) 透传在 navigate state）
  → 创建 analysis（含 scenario_payload.pending_review_task_id）
  → process_analysis_v2 完成后
      ├─ analysis_service.py:126 同步创建新 ReviewTask ← 罪魁
      └─ analysis.py:395 也创建 ReviewTask（后加的兜底逻辑）
  → ResultPage patch 原始 reminder → completed
  → 新 ReviewTask 也计入未完成数 → 29 + 1 - 1 = 29（抵消）
```

直接入口（无 pending_review_task_id）行为不变：正常创建 ReviewTask，29→29。

## Goals / Non-Goals

**Goals：**
- ReviewsPage 入口完成后，未完成 reminder 净减少 1（29→28）
- 直接入口行为不变（29→29）
- 不引入破坏性变更

**Non-Goals：**
- 不修其他入口的 ReviewTask 创建逻辑
- 不改 patch review API 语义

## Decisions

### Decision 1: 传递信号的位置

ReviewsPage 传来的 `pendingReviewTaskId` 已在 navigate state 中，需要透传到后端。

- **选项 A**：新增专用请求头 `X-Pending-Review-Task-Id`
  - 缺点：需要改 API 契约，Swagger/OpenAPI schema 要同步更新
- **选项 B（选这个）**：复用 `scenario_payload.pending_review_task_id`
  - 优点：不改 API 契约，现有 schema 天然支持任意 key
  - 透传路径：ReviewsPage → navigate(state) → PostTradeInput → `/api/v1/analysis` body → 后端

### Decision 2: 跳过创建的时机

两个位置都会创建 ReviewTask：

1. `analysis_service.py:126` — `create_analysis_task` 同步创建（用户提交后立即可见）
2. `analysis.py:395` — `process_analysis_v2` completion 兜底创建

若只修其中一处，另一处仍会创建。**两处均修**，判断条件统一：`scenario == "post_trade_review" AND scenario_payload.get("pending_review_task_id")` 有值。

### Decision 3: 直接入口不变化

直接入口（用户主动发起 post_trade_review，无 pending_review_task_id）的 `scenario_payload` 不含此 key，`should_skip_review_task = False`，行为与修改前完全一致。

## Risks / Trade-offs

[Risk] 新 analysis 完成但用户未在 ResultPage 点 confirm/later，原始 reminder 被标记完成，但新 analysis 对应的 ReviewTask 未创建
→ **评估**：这个场景在 ReviewsPage 入口下不存在，因为 patch 原始 reminder 是用户点了"确认/稍后"才触发的，两者绑定在同一交互内

[Risk] `pending_review_task_id` 指向的 UUID 在 DB 中不存在（幽灵 ID）
→ **评估**：不影响跳过逻辑（条件是 `get()` 有值即跳过）；ResultPage patch 步骤会 404，但用户仍停留在 ResultPage，可继续操作，无阻塞风险

## Migration Plan

1. **smoke 验证（本次）**
   - 手动跑 ReviewsPage 入口：基线 29 → patch 原始 reminder → 分析完成 → 最终 28
   - 手动跑直接入口：基线 29 → 分析完成 → 最终 29（不变）
   - 验证 patch 原始 reminder 后 DB status=COMPLETED

2. **代码收口（本次）**
   - analysis_service.py:120-122 跳过逻辑
   - analysis.py:388-391 跳过逻辑
   - PostTradeInput.tsx:63 透传逻辑

无回滚需求：新增的 if 分支不影响现有逻辑路径。
