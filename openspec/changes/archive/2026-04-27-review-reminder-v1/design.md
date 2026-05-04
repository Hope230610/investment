## Context

本 change 的目标是把“待复盘提醒”从首页局部信息升级为跨页面可感知的壳层提醒，并统一 `pending` / `expired` / `completed` 三类状态在首页、复盘页和底部导航中的语义。

当前仓库已经具备一部分实现基线：

- `investment-front/src/App.tsx` 内部 `AppShell` 已能在 Reviews tab 渲染角标，并在 mount 时调用 `GET /api/v1/reviews`
- `investment-front/src/utils.ts` 已提供 `computeUnfinishedReviews`、`computeOverdueDays`、`sortUnfinishedReviews`
- `investment-front/src/pages/HomePage.tsx` 已按 `expired -> pending` 排序提醒卡
- `investment-front/src/pages/ReviewsPage.tsx` 已给 `expired` 卡片增加红色样式和逾期天数

当前差距也很明确：

1. change 文档中的 capability 名仍写成 `review-loop`，未对齐 baseline `history-and-review-loop`
2. badge 数据刷新仍是 mount-only；用户在一次会话内完成复盘后，返回壳层页面时可能看到旧计数
3. `ReviewsPage.tsx` 仍直接按状态筛选，和“共享 util 作为唯一口径”的目标未完全对齐
4. 原文中的“Verified Implementation”与仓库现状不一致，文件名、复用范围和 lint/build 结论都需要按真实状态回写

## Goals / Non-Goals

**Goals：**

- 用统一口径展示“未完成复盘数”=`pending + expired`
- 让用户在首页、复盘页和底部导航中都能优先感知 `expired` 任务
- 在不改后端契约的前提下，把前端提醒逻辑收敛到共享计算函数

**Non-Goals：**

- 不新增后端接口、专用 badge API 或数据库字段
- 不做推送通知、PWA badge、轮询或 websocket 实时同步
- 不修改 `review_tasks` 创建链路和 `post_trade_review` 输入/输出契约

## Decisions

### Decision 1: capability 归属收敛到 `history-and-review-loop`

本次 change 只改变“未完成复盘任务如何被读取、排序和提醒”，不改变 `post-trade-review` 的结构化输入、归因输出或任务创建契约，因此 capability 归属收敛到既有 `history-and-review-loop`。

**不选的方案：**

- 保留 `review-loop`：会和 baseline spec 命名分叉，后续 archive/verify 无法稳定对齐
- 同时声明 `post-trade-review`：会把纯提醒层变更误写成复盘输入/输出契约变更

### Decision 2: badge 语义固定为“未完成复盘数”

底部导航 Reviews tab 的角标数值固定为 `pending + expired`，`completed` 不计入。视觉上：

- `count = 0`：不显示角标
- 仅有 `pending`：橙色提醒
- 只要存在 `expired`：红色提醒
- 数值超过 99：显示 `99+`

这个定义和首页提醒区、复盘页待处理分组保持同一口径，避免用户在不同页面看到不同“待办数”。

### Decision 3: badge 新鲜度采用“壳层路由切换 + window focus 刷新”

`App.tsx` 中的 `AppShell` 继续持有 `unfinishedReviews` state，但刷新触发不能停留在 mount-only。设计目标为：

- 首次进入壳层页面时拉取一次
- `location.pathname` 切回任一主导航页时重新拉取
- 浏览器窗口重新获得焦点时重新拉取

这样可以覆盖“用户完成复盘后返回首页/复盘页”“切后台再回来”两类高频路径，同时避免为了一个小角标引入轮询或实时通道。

**不选的方案：**

- 仅 mount 时拉取：会产生会话内 stale badge
- 固定间隔轮询：额外流量和状态抖动都不值得

### Decision 4: 未完成任务计算统一走共享 util，并在失败时静默降级

前端统一复用：

- `computeUnfinishedReviews(reviews)`：筛出 `pending + expired`
- `sortUnfinishedReviews(tasks)`：`expired` 优先，同状态按 `review_at` 升序
- `computeOverdueDays(reviewAt)`：计算逾期天数

如果 `GET /api/v1/reviews` 拉取失败：

- 底部导航角标直接隐藏，不展示过期的旧计数
- 首页、复盘页继续走各自已有的空状态/降级状态
- 不因为提醒失败阻断主导航使用

## Technical Design

### Data / Interface Boundary

- 继续复用现有 `GET /api/v1/reviews`
- 不新增前端缓存持久化，不把 badge count 写入 localStorage
- 不新增后端字段、索引、migration 或聚合接口

### State Flow

```text
AppShell 首次进入壳层页 / pathname 切换 / window focus
  → GET /api/v1/reviews
  → computeUnfinishedReviews(reviews)
  → badgeCount = unfinished.length
  → hasExpired = unfinished.some(status === 'expired')
  → count = 0 时不渲染角标
  → count > 0 时渲染 badge（expired 存在则红色，否则橙色）
```

### UI Semantics

**底部导航 Reviews tab**

- 角标只表达“未完成复盘数”，不是“全部复盘记录数”
- 颜色优先级由是否存在 `expired` 决定，而不是由当前页面是否激活决定
- `AppShell` 只是状态持有位置；实现文件仍然是 `investment-front/src/App.tsx`

**HomePage 待复盘提醒区**

- 仅展示 `pending + expired`
- `expired` 排在 `pending` 之前
- 同状态内按 `review_at` 升序
- `expired` 卡片显示红色“已逾期 N 天”标签

**ReviewsPage 待处理列表**

- `expired` 卡片使用红色边框 + 浅红背景 + “已逾期 N 天”
- `pending` 保持普通提醒样式
- `completed` 不进入待处理列表，并继续在已完成分组中展示完成时间

### File Structure

```text
investment-front/src/
├── App.tsx                    # AppShell 定义、badge state 与刷新触发
├── utils.ts                   # unfinished / overdue / sort 共享计算
└── pages/
    ├── HomePage.tsx           # 首页待复盘提醒区排序与 expired 标签
    └── ReviewsPage.tsx        # 待处理列表中的 expired 强调
```

### Async / Security / Monitoring

- **异步边界**：角标刷新是幂等读操作，不影响复盘提交链路；失败时仅影响提醒显示，不影响导航和页面主体内容
- **安全边界**：继续依赖现有鉴权后的 `/api/v1/reviews`，不新增跨用户聚合或新的敏感字段读取
- **监控影响**：本 change 不引入新的后端指标；前端至少应保留 badge 刷新失败的可观测点（开发期 `console.warn` 或后续 telemetry event），便于排查“角标不更新”类问题

## Current Verification Snapshot

2026-04-22 本地仓库核对结果：

- `npm test`：通过，`vitest` 46/46
- `npm run build`：通过，但仍有现存 chunk size warning
- `npm run lint`：通过；此前由 `src/utils/learningFeedback.test.ts` 中预存的 Storage mock / `beforeEach` 类型问题导致的阻塞已单独收口

与设计目标相比，当前代码状态已经完成本 change 的核心前端收口：

- 已有：`App.tsx` badge 渲染、主导航页 pathname 切换刷新、window focus 刷新、拉取失败时清空旧角标
- 已有：`HomePage.tsx` 排序、`ReviewsPage.tsx` 过期强调、`utils.ts` 统一 unfinished / overdue / sort 计算
- 剩余风险：手动 smoke 尚未完成；`build` 仍有现存 chunk size warning，但非本 change 新引入

## Migration Plan

1. **Contract 收口**
   - 新增 `history-and-review-loop` delta spec，明确角标口径、过期优先级和会话内刷新要求
   - 同步 `.openspec.yaml`、`proposal.md`、`tasks.md` 的 capability 命名

2. **Frontend 收口**
   - 在 `App.tsx` 中把 badge 数据刷新从 mount-only 改为 shell route / focus refresh
   - 在 `ReviewsPage.tsx` 中复用 `computeUnfinishedReviews`，避免口径分叉
   - 保持 `GET /api/v1/reviews` 为唯一数据源，不引入额外 API

3. **QA / Release**
   - 继续保留 `npm test`、`npm run build` 作为实现级校验
   - `npm run lint` 需等现存 `learningFeedback.test.ts` 问题单独收口后再恢复为 release gate
   - 手动 smoke：无待办 / 仅 pending / 存在 expired / 完成复盘后返回首页四条路径都要跑通

## Open Questions

1. 当前迭代是否只依赖“壳层路由切换 + focus”刷新就足够？
   - 暂时足够。现有复盘动作主要发生在输入页/结果页，离开后会重新进入壳层页面；后续如果在壳层内也能直接完成任务，再补显式 refresh event。

2. badge 刷新失败是否要上报正式埋点？
   - 本次先不把 telemetry 作为交付阻塞项，但设计上保留可观测点，避免后续只能靠用户口头反馈排查。
