## MODIFIED Requirements

### Requirement: 用户画像必须收口到最小集

系统 MUST 将用户画像收口到经验层级、持有周期、风险承受偏好、行为标签和画像来源这组最小必要信息。枚举值和标签口径 MUST 与统一 contract 保持一致，重复标签必须被收敛，且画像结构中不得混入手机号、邮箱，资金规模、持仓明细等非必要身份或高敏字段。

**迁移说明**：`user_profiles` 表移除以下已废弃字段：`investment_goals`、`portfolio_size`、`preferred_sectors`。基线定义字段集：`experience_level`、`holding_horizon`、`risk_tolerance`、`behavior_tags`、`profile_source`。历史数据中废弃字段值直接清理，不做映射迁移。

#### Scenario: 提交未定义的画像枚举值
- **WHEN** 客户端提交不在约定枚举范围内的画像字段值
- **THEN** 系统拒绝更新请求，并返回明确的参数校验错误

### Requirement: 分析任务必须锁定画像快照

系统 SHALL 在创建依赖用户画像的分析或复盘任务时保存当前画像快照，并且该快照 MUST 只包含约定的最小画像信息。任务创建后的快照不得因为用户后来修改画像而被回写，用于确保分析结果可追溯到当时的用户适配上下文。

**迁移说明**：`analysis_tasks.user_profile_snapshot` 按基线 JSON schema 存储，不含废弃画像字段。快照与 `user_profiles` 完全独立修改路径。

#### Scenario: 用户修改画像后回看旧分析
- **WHEN** 用户在分析任务创建后更新了自己的画像，并再次查看旧分析结果
- **THEN** 旧分析仍关联创建当时的画像快照，而不是被新画像覆盖
