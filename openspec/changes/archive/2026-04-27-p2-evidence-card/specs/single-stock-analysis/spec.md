# single-stock-analysis: 结果页证据化扩展（p2-evidence-card 实施记录）

## Purpose

本 delta spec 是 `p2-evidence-card` 变更的实施记录，更新 `single-stock-analysis` baseline spec 的 `Requirement: 单股咨询结果必须输出六段式决策卡`，确认 `DecisionCardV2` 已扩展为包含支撑证据、反方证据、失效条件和置信度等级的结构。

## MODIFIED Requirements

### Requirement: 单股咨询结果必须输出六段式决策卡

**旧表述：** 系统 SHALL 在单股咨询结果可读时返回完整决策卡。该决策卡 MUST 同时覆盖判断结论、关键信号摘要、用户适配说明、下一步动作、主要风险和复查时点六类信息；结果还必须包含至少一个可展示的复查时间或失效条件说明，避免结论被长期误用。

**新表述：** 系统 SHALL 在单股咨询结果可读时返回完整决策卡。该决策卡 MUST 同时覆盖判断结论、关键信号摘要、用户适配说明、下一步动作、主要风险和复查时点六类信息，**并且额外包含支撑证据列表、反方证据列表、失效条件列表和置信度等级**。

扩展后的决策卡字段（共 10 个）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `headline_judgement` | string | 核心判断 |
| `key_reason_summary` | `ReasonPoint[]` | 关键理由（含 OutputMarkType） |
| `user_fit_summary` | `{fit, unfit}` | 用户适配说明 |
| `next_step_actions` | `string[]` | 下一步动作 |
| `primary_risks` | string | 主要风险（段落） |
| `review_at` | datetime | 建议复查时间 |
| `supporting_evidence` | `string[]` | 支撑证据（本次新增） |
| `counter_evidence` | `string[]` | 反方证据（本次新增） |
| `invalidation_conditions` | `string[]` | 失效条件（本次新增） |
| `confidence_level` | `low \| medium \| high` | 置信度等级（本次新增） |

#### Scenario: 决策卡输出完整证据结构
- **WHEN** 单股咨询结果可读时
- **THEN** 系统返回包含支撑证据、反方证据、失效条件和置信度等级的决策卡
- **AND** `counter_evidence` 与 `key_reason_summary` 角度互补，不重复

#### Scenario: 置信度不得默认高
- **WHEN** 系统生成决策卡
- **THEN** 置信度必须由数据质量和风险指标计算
- **AND** 数据完整度低或风险得分高时，`confidence_level` MUST NOT be `high`

## Alignment Summary

B2（本次变更）完成后：
- ✅ 每张分析卡必须有 `counter_evidence`（反方证据）
- ✅ 每张分析卡必须有 `confidence_level`（置信度）
- ✅ 前端展示区明确区分"支撑证据"和"反方证据"
- ✅ 置信度不得默认 high

## Pending

- 手动 smoke 验证（见 tasks.md 3.2）
