## Purpose

定义历史记录回看、复盘任务生命周期和过期重评估语义，确保分析结果能够形成长期可追踪的使用闭环。本 spec 重点防止结果"生成即结束"，要求系统支持后续回看、复盘和重新评估，而不规定具体分页字段名或接口对象命名。

## Requirements

### Requirement: 历史记录查询必须可分页回看
系统 SHALL 提供用户历史分析记录的分页回看能力，并遵循统一的分页语义。历史记录 MUST 至少支持用户按本人范围回看分析场景、生命周期状态、创建时间和结果摘要。

#### Scenario: 用户查看历史记录列表
- **WHEN** 用户请求自己的历史分析记录
- **THEN** 系统返回分页结果，并且只包含该用户自己的记录

### Requirement: 复盘任务必须有完整生命周期
系统 SHALL 对复盘任务使用统一生命周期管理，至少覆盖待处理、已完成和已过期三类业务状态，并提供读取和完成能力。任何复盘任务状态变更 MUST 与对应的分析记录和用户归属建立可追溯关联。

复盘任务的完成操作 SHALL 通过两步行为完成：
- **Step1**：写入 emotion_history 和 judgment_history（画像学习）
- **Step2**：更新对应 review_task 的 status 为 completed

两步均需成功才算完成。任何一步失败（包括 404 Not Found），系统 SHALL 记录结构化日志但不向用户展示错误。失败不得导致前端静默标记为"已处理"。

#### Scenario: 用户完成复盘任务（两步均成功）
- **WHEN** 用户在结果页点击 feedback card 的"确认"按钮，且 Step1（画像写入）和 Step2（review_task 更新）均返回 2xx
- **THEN** 系统关闭卡片，且 emotion_history 有新记录、review_tasks.status 为 completed

#### Scenario: Step2 失败（ReviewTask 不存在）
- **WHEN** 用户点击"确认"，Step1 返回 2xx，但 Step2 返回 404（ReviewTask 未找到）
- **THEN** 系统关闭卡片、记录结构化日志（含 analysis_task_id 和错误码），但 review_tasks.status 保持不变。不得向用户展示错误。

#### Scenario: Step1 失败
- **WHEN** 用户点击"确认"，Step1 返回 500 或其他错误
- **THEN** 系统关闭卡片并记录错误，不标记为已处理。下次打开结果页时卡片仍可弹出。

### Requirement: 结果回看必须处理过期与再评估
系统 MUST 在分析结果超过有效期后，将其标记为已过期或明确提示需要重新评估。用户回看过期结果时，系统 SHALL 提示该结论不可继续作为当前操作依据，并提供重新分析或重新复盘的入口语义。

当用户对过期结果提交复盘反馈时，系统 SHALL 接受反馈并写入 emotion_history 和 judgment_history，即使 review_task.status 为已过期状态也不例外（用户可对历史结果做新的学习记录）。

#### Scenario: 用户对过期结果提交 learning feedback
- **WHEN** 用户打开已过期分析结果，并在反馈卡中点击"确认"
- **THEN** 系统将 emotion_level 和 judgment_score 写入 emotion_history/judgment_history，即使对应的 review_task.status 已为过期状态。review_task.status 保持不变（不再更新为已完成）。

#### Scenario: 用户打开已过期分析结果
- **WHEN** 用户查看超过有效期的历史分析结果
- **THEN** 系统展示过期状态，并提示用户重新评估而不是继续沿用旧结论

### Requirement: 未完成复盘任务必须提供跨页面提醒与过期优先语义
系统 SHALL 在主导航壳层页面、首页提醒区和复盘任务页中，使用统一口径展示未完成复盘任务。未完成复盘数 MUST 定义为 `pending + expired`，`completed` MUST 不计入角标或首页提醒区。

当存在 `expired` 任务时，系统 MUST 使用高于 `pending` 的视觉优先级，以确保用户能优先感知已过期任务。

#### Scenario: 用户在底部导航感知未完成复盘
- **WHEN** 用户进入任一主导航壳层页面
- **AND** 系统存在 `pending` 或 `expired` 复盘任务
- **THEN** 复盘入口显示未完成复盘数角标，或由后续提醒中心入口承接同等提醒语义
- **AND** 角标数值等于 `pending + expired`
- **AND** 仅有 `pending` 时使用普通提醒色，存在 `expired` 时使用更高紧急色

#### Scenario: 用户没有未完成复盘任务
- **WHEN** 用户进入任一主导航壳层页面
- **AND** 系统不存在 `pending` 或 `expired` 复盘任务
- **THEN** 复盘提醒入口不显示角标

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
- **AND** 用户不需要手动刷新整个页面才能看到新的提醒数量
