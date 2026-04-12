## MODIFIED Requirements

### Requirement: 交易前自检必须使用结构化输入

系统 SHALL 要求交易前自检以结构化方式表达最小决策上下文。请求 MUST 至少说明用户准备采取的动作和触发该动作的背景，并允许补充情绪状态、原计划和当前偏离点等信息，用于判断当前行为是否偏离原计划。

**迁移说明**：底层实现从 `analyses` 表迁移到 `analysis_tasks` 表，`scenario_payload` 按 `pre_trade_check` 结构存储输入数据。

#### Scenario: 创建交易前自检任务
- **WHEN** 用户提交包含最小决策上下文的合法自检请求
- **THEN** 系统创建本次自检并返回可追踪的处理状态

### Requirement: 行为干预必须高于常规分析结论

系统 SHALL 在识别到追涨、恐慌卖出、频繁交易等高风险行为偏差时，优先输出行为干预结论。行为干预 MUST 先于常规判断展示，并明确解释触发原因、风险级别和建议的冷静期或等待条件。

**迁移说明**：行为干预从内嵌 JSON（`analyses.intervention`）迁移到独立 `behavior_interventions` 表，`analysis_results.intervention` 仅存储引用 ID。

#### Scenario: 识别到高风险追涨行为
- **WHEN** 交易前自检请求显示用户因热点或情绪高涨准备追涨买入
- **THEN** 系统优先返回行为干预内容，而不是直接给出继续操作的倾向性结论

### Requirement: 高风险自检只允许保守下一步动作

系统 MUST 在高风险或降级场景下，将后续动作限定为等待、补充验证、自检问题、冷静期、复查等保守动作，不得通过自检结果直接推动用户立即买入、加仓、减仓或卖出。

**迁移说明**：`analysis_results.detail_panels.degrade_flags` 字段记录降级原因，`next_step_actions` 在高风险时强制限定为保守动作。

#### Scenario: 自检结果处于高风险状态
- **WHEN** 自检结果判定为高风险行为偏差或证据不足
- **THEN** 系统只输出保守动作建议，并明确说明为什么当前不适合立刻操作
