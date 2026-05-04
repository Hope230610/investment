## ADDED Requirements

### Requirement: 未完成复盘任务必须提供跨页面提醒与过期优先语义

系统 SHALL 在主导航壳层页面、首页提醒区和复盘任务页中，使用统一口径展示未完成复盘任务。未完成复盘数 MUST 定义为 `pending + expired`，`completed` MUST 不计入角标或首页提醒区。

当存在 `expired` 任务时，系统 MUST 使用高于 `pending` 的视觉优先级，以确保用户能优先感知已逾期任务。

#### Scenario: 用户在底部导航感知未完成复盘

- **WHEN** 用户进入任一主导航壳层页面
- **AND** 系统存在 `pending` 或 `expired` 复盘任务
- **THEN** Reviews tab 显示未完成复盘数角标
- **AND** 角标数值等于 `pending + expired`
- **AND** 仅有 `pending` 时使用普通提醒色，存在 `expired` 时使用更高紧急色

#### Scenario: 用户没有未完成复盘任务

- **WHEN** 用户进入任一主导航壳层页面
- **AND** 系统不存在 `pending` 或 `expired` 复盘任务
- **THEN** Reviews tab 不显示角标

#### Scenario: 用户查看首页待复盘提醒区

- **WHEN** 首页存在未完成复盘任务
- **THEN** 系统只展示 `pending + expired` 任务
- **AND** `expired` 排在 `pending` 之前
- **AND** 同状态内按 `review_at` 升序排列

#### Scenario: 用户查看复盘任务页中的过期任务

- **WHEN** 某复盘任务状态为 `expired`
- **THEN** 系统以高于 `pending` 的视觉样式展示该任务
- **AND** 系统显示该任务的逾期天数
- **AND** `completed` 任务不进入待处理列表

#### Scenario: 用户在同一次会话中返回壳层页面

- **WHEN** 用户完成一次复盘或切换回任一主导航壳层页面
- **THEN** 系统基于最新的 review 列表重新计算未完成复盘数
- **AND** 用户不需要手动刷新整个页面才能看到新的角标数量
