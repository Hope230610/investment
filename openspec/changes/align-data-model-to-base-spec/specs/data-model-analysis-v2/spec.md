## Purpose

定义分析任务（analysis_tasks）与分析结果（analysis_results）分离后的数据结构规范，支持 `partial_ready` 中间状态，满足单股咨询、交易前检查、交易后复盘三个场景的结构化输入输出。

## Requirements

### Requirement: 分析任务必须包含输入快照
系统 SHALL 在创建分析任务时保存用户画像快照和场景输入数据。画像快照 MUST 仅包含经验层级、持有周期、风险偏好、行为标签和来源五个字段，不得混入手机号、邮箱或资金规模等高敏字段。

#### Scenario: 创建分析任务时保存画像快照
- **WHEN** 用户提交任意场景（单股咨询/交易前检查/交易后复盘）的分析请求
- **THEN** 系统在 `analysis_tasks` 中保存当时的 `user_profile_snapshot`，快照不得在后续被用户画像变更回写

### Requirement: 分析结果必须包含六段式决策卡
系统 SHALL 在分析完成后返回六段式决策卡，至少包含判断结论、关键理由摘要、用户适配说明、下一步动作、主要风险和复查时点。

#### Scenario: 查看分析结果
- **WHEN** 用户查看已完成分析任务的结果
- **THEN** 系统从 `analysis_results` 返回六段式决策卡，并附带 `valid_period` 有效期

### Requirement: 分析结果必须包含降级标记
系统 SHALL 在外部数据源不足、模型推理受限或关键证据缺失时设置 `degrade_flags`，并在下一次动作中限定为观察、等待、补充信息等安全动作，不得输出直接买卖建议。

#### Scenario: 关键行情数据缺失
- **WHEN** 分析过程中缺少关键行情或公告信息
- **THEN** 系统在 `detail_panels.degrade_flags` 中记录 `missing_<data_source>`，下一次动作限定为安全动作

### Requirement: 行为干预必须独立存储
系统 SHALL 将行为干预写入独立 `behavior_interventions` 表，不得以内嵌 JSON 方式混入 `analyses` 表。干预记录 MUST 支持按用户查询、高频干预识别和冷静期追踪。

#### Scenario: 识别高风险行为偏差
- **WHEN** 分析引擎识别到追涨/恐慌卖出/频繁交易行为
- **THEN** 系统将干预写入 `behavior_interventions` 表，并通过 `intervention` JSON 字段与 `analysis_results` 关联
