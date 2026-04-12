## MODIFIED Requirements

### Requirement: 单股咨询必须以结构化任务创建

系统 SHALL 允许已登录用户发起单股咨询，并以结构化方式表达目标标的、关注背景和时间视角等最小上下文。系统接受请求后 MUST 返回可追踪的处理引用、当前处理状态以及可展示的等待说明，确保用户知道本次咨询已经进入受管生命周期。

**迁移说明**：底层实现从 `analyses` 表迁移到 `analysis_tasks` 表，API 层内部路由切换，对外接口语义不变。

#### Scenario: 创建单股咨询任务
- **WHEN** 已登录用户提交合法的单股咨询请求
- **THEN** 系统创建该次咨询并返回可追踪的处理引用

### Requirement: 单股咨询结果必须输出六段式决策卡

系统 SHALL 在单股咨询结果可读时返回完整决策卡。该决策卡 MUST 同时覆盖判断结论、关键理由摘要、用户适配说明、下一步动作、主要风险和复查时点六类信息；结果还必须包含至少一个可展示的复查时间或失效条件说明，避免结论被长期误用。

**迁移说明**：结果数据从 `analyses.decision_card + analyses.reasons` 迁移到 `analysis_results` 表，`headline_judgement` 字段对应原 `headline`，`detail_panels.facts/inferences/uncertainties` 来自原 `analysis_reasons` 表按 `mark_type` 分类聚合。

#### Scenario: 单股咨询结果准备完成
- **WHEN** 用户查看已经生成可读结果的单股咨询
- **THEN** 系统返回包含六段式决策卡和复查时间的标准结果结构

### Requirement: 单股咨询必须支持统一状态轮询

系统 SHALL 允许用户持续追踪单股咨询的处理状态，并且状态语义 MUST 与共享状态口径保持一致。结果进入部分可读或完全可读阶段时，系统 MUST 同时告知当前是否存在降级、适配摘要和必要的后续复盘提示，避免用户误以为处理中结果已经等同于完整结论。

**迁移说明**：新增 `partial_ready` 状态对应 `analysis_tasks.status = "partial_ready"`，原 `processing` 状态保留语义不变。

#### Scenario: 轮询部分可用结果
- **WHEN** 单股咨询进入部分可读状态
- **THEN** 系统返回当前可展示结果、`degrade_flags` 降级提示与用户可执行的下一步动作
