## Why

当前决策卡只有"结论 + 风险 + 失效时间"，缺少支撑证据、反方证据和置信度。这让结果更像"分析内容"而不是"决策证据卡"——用户无法判断结论可靠程度，也无法看到持不同意见的理由。产品从 MVP 升级到可信闭环，必须补上这两个字段。

## What Changes

- `DecisionCardV2` 新增 4 个结构化字段：`supporting_evidence[]`、`counter_evidence[]`、`invalidation_conditions[]`、`confidence_level`
- `AnalysisGenerationService` 在 `_build_decision_card` 中生成上述 4 个字段，规则：低数据质量不得输出 high 置信度
- `ResultPage.tsx` 新增两个独立展示区：支撑证据（绿色）+ 反方证据（红色），并展示置信度 Badge
- `types.ts` 同步更新 `DecisionCardV2` 类型
- `GetAnalysisResponseV2` 透传新字段到前端

## Capabilities

### New Capabilities
- `evidence-card`: 六段式决策卡的证据结构化扩展，要求每张卡同时包含支撑证据、反方证据、失效条件和置信度等级，支撑证据与反方证据必须分区展示，置信度不得默认高

### Modified Capabilities
- `single-stock-analysis`: 更新 `Requirement: 单股咨询结果必须输出六段式决策卡`，扩展决策卡必须包含的字段清单（增加 evidence 结构）

## Impact

**受影响区域：**
- `investment-back/src/schemas/analysis.py` — `DecisionCardV2`、`GetAnalysisResponseV2` 加字段
- `investment-back/src/services/analysis_generation_service.py` — `_build_decision_card` 生成新字段
- `investment-front/src/types.ts` — `DecisionCardV2` 类型同步
- `investment-front/src/pages/ResultPage.tsx` — UI 新增两个证据展示区 + 置信度 Badge

**关联基线文档：**
- `structure/investment_current_implementation_gap_audit.md` — P0 收尾任务

**不受影响：**
- API 路由层（payload 透传，不改变接口路径）
- 数据库模型（字段在服务层构造，不新增表列）
