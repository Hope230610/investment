## MODIFIED Requirements

### Requirement: 复盘任务必须有完整生命周期

系统 SHALL 对复盘任务使用统一生命周期管理，至少覆盖待处理、已完成和已过期三类业务状态，并提供读取和完成能力。任何复盘任务状态变更 MUST 与对应的分析记录和用户归属建立可追溯关联。

**迁移说明**：`review_tasks` 外键从 `analyses.id` 改为 `analysis_tasks.id`。`review_tasks.analysis_task_id` 建立唯一约束，防止重复关联。

#### Scenario: 用户完成复盘任务
- **WHEN** 用户提交某个待处理复盘任务的完成动作
- **THEN** 系统将该任务更新为已完成状态，并保留与原分析记录的关联
