## Why

当前 `AppShell` 的底部导航 Reviews tab 缺少感知锚点，用户在首页或其他页面时无法感知自己仍有未完成复盘任务，导致复盘闭环激活率偏低。当前系统已具备复盘任务列表与过期状态标记能力，但仍缺少两项关键体验：

1. **Tab 角标**：跨页面感知"仍有未完成复盘任务"
2. **过期强调**：`expired` 任务虽已过期，但本质仍属待处理任务；当前视觉权重与 `pending` 相同，紧迫程度不够突出

## What Changes

- `AppShell` 底部导航 Reviews tab 增加未完成复盘数角标（`pending + expired`）
- `ReviewsPage` 对 `expired` 任务增加红色边框/背景，并显示"已逾期 N 天"
- `HomePage` 复盘提醒区按紧迫程度排序：`expired` 优先于 `pending`，同状态内按时间升序排列

> **不做**：推送通知 / PWA badge / 修改 `review_tasks` 创建逻辑 / 修改后端接口 / 新增 badge 专用接口

## Capability Semantics

- 角标语义为**未完成复盘数**，不是"正常待办数"
- `expired` 仍计入角标，因为其本质上仍为待处理任务，只是优先级高于 `pending`
- `completed` 不计入角标，也不进入首页提醒区

## Capabilities

### Modified Capabilities

- `history-and-review-loop`：底部导航、首页提醒区和复盘页对未完成复盘任务采用统一口径提醒；`expired` 任务优先于 `pending` 展示，并在壳层页面提供跨页面感知入口

## Impact

- 关联结构文档：`structure/investment_team_execution_board.md`、`structure/ai_investment_decision_system_ui_structure_design.md`、`structure/investment_production_system_architecture.md`
- 执行板泳道：`TASK-FE-103 优化首页回流入口`（留存阻塞）
- 前端影响范围：`App.tsx`（内含 `AppShell`）、`utils.ts`、`ReviewsPage.tsx`、`HomePage.tsx`
- 后端影响范围：无（复用现有 `GET /api/v1/reviews`）
- 数据模型影响：无
- 发布影响：无 migration；以视觉与交互变更验证
- 实现约束：前端应复用统一的“未完成复盘数”计算逻辑，并且 badge 至少要在壳层路由切换时刷新，避免仅 mount 读取导致 stale count
