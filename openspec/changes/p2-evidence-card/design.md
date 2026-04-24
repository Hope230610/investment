## Context

**现状：** `DecisionCardV2`（后端 schema）只有 `headline_judgement`、`key_reason_summary`、`user_fit_summary`、`next_step_actions`、`primary_risks`、`review_at` 六个字段。`AnalysisGenerationService` 的 `_build_decision_card` 只填充 `primary_risks`（一段文字）和 `review_at`/`valid_until`（时间戳），没有独立的支撑证据、反方证据、失效条件和置信度字段。前端 `ResultPage.tsx` 的决策卡 UI 只有"核心理由"（key_reason_summary）和"主要风险与失效条件"两个展示区，置信度完全缺失。

**目标：** 扩展 `DecisionCardV2` 为八字段结构，每张决策卡同时包含支撑证据、反方证据、失效条件和置信度等级，且置信度必须由规则计算，不得默认 high。

**约束：** 不改 API 路由层（`GetAnalysisResponseV2` 只透传字段），不新增数据库表列（字段在服务层构造），不改 `DecisionCard`（旧路径兼容）。

## Goals / Non-Goals

**Goals:**
- `DecisionCardV2` 新增 4 个结构化字段：`supporting_evidence`、`counter_evidence`、`invalidation_conditions`、`confidence_level`
- 置信度由 `_build_metrics` 的数据质量指标计算，规则透明可测，不得硬编码
- 前端 `ResultPage.tsx` 新增两个独立展示区（绿色支撑 / 红色反方）+ 置信度 Badge
- 兼容 `AnalysisDetail` 前端类型 + `GetAnalysisResponseV2` 后端 schema

**Non-Goals:**
- 不改变 API 接口路径（字段在现有 payload 内扩展）
- 不修改旧路径 `DecisionCard`（Phase 1 兼容）
- 不做 LLM prompt 改造（当前是规则生成，后续合规模板化阶段处理）

## Decisions

### Decision 1: 置信度计算规则

**选项 A：** 直接在 `_build_decision_card` 中基于 `risk_score` + `data_completeness` 映射为 `low/medium/high`
**选项 B：** 新增独立 `ConfidenceLevel` 计算方法，接收 metrics dict

**选择：A（推荐）**

理由：metrics 已经包含 `risk_score`（0-5）和 `data_completeness`（0-3），这两个指标恰好是置信度的核心驱动因子。在已有方法内计算，无需新增依赖，符合最小改动原则。

**置信度映射规则：**
```
if data_completeness <= 1:
    confidence = 'low'
elif risk_score >= 3:
    confidence = 'low'
elif risk_score >= 2 or data_completeness == 2:
    confidence = 'medium'
else:
    confidence = 'high'
```
注：`high` 只在数据完整且风险可控时输出，禁止默认 high。

### Decision 2: 反方证据生成策略

**选项 A：** 从 `recent_events` 中提取风险关键词作为反方证据
**选项 B：** 从 `key_reason_summary` 推断持不同观点的理由

**选择：A（推荐）**

理由：`key_reason_summary` 主要表达为什么当前判断成立；反方证据需要结构化表达"哪些信号支持相反判断"。当 `risk_score >= 2` 时，系统应明确输出"如果这些风险兑现，判断方向可能反转"；当数据不完整时，输出"信息不足时不宜过度乐观/悲观"。逻辑与 `_build_event_reason` 互补，不重复。

**生成逻辑：**
- `risk_score >= 2` → 至少 1 条反方证据，说明"如果 X 风险兑现，则判断反转"
- `data_completeness <= 1` → 反方证据指向"数据不足，当前结论不可靠"
- `recent_events` 有风险事件 → 以事件标题为锚点生成反方理由
- 否则 → 通用反方："如果短期催化剂消失，当前进场逻辑需重新评估"

### Decision 3: 失效条件（invalidation_conditions）

**选项 A：** 复用 `primary_risks` 作为失效条件
**选项 B：** 新增独立 `invalidation_conditions[]` 列表

**选择：B**

理由：`primary_risks` 当前是 string（段落），描述"风险是什么"；`invalidation_conditions` 需要 list of strings，描述"什么情况下这张卡必须重新评估"。两者语义不同，必须独立字段。例如：`primary_risks = "波动性风险..."`；`invalidation_conditions = ["放量下跌超过 5%", "出现监管问询公告", "有效期内涨跌幅超过 ±15%"]`。

**生成逻辑：** 固定 3 条，基于场景类型和 metrics 生成：
- 通用失效条件：超过 `valid_until`、出现风险关键词公告
- 场景特定失效条件：`single_stock` 关注价格突破、`pre_trade` 关注情绪变化

## Risks / Trade-offs

**[Risk]** 置信度规则可能产生误判，例如 data_completeness=3 但 recent_events 为空时 confidence 过高
→ **Mitigation：** `risk_score` 考虑了事件风险和波动率，即使数据完整也会被压低置信度。后续通过 smoke 测试验证边界情况。

**[Risk]** 反方证据可能与支撑证据语义重复
→ **Mitigation：** 生成逻辑确保两者角度互补（支撑 = "为什么这样判断"，反方 = "什么情况下判断反转"），语义不重叠。

**[Risk]** 新增字段后，前端未展示时会产生数据空洞（undefined）
→ **Mitigation：** `AnalysisGenerationService` 的所有 `_build_*_result` 方法必须全部填充这 4 个字段，不存在 undefined 路径。

## Migration Plan

1. **Phase 1（后端）：** 修改 `DecisionCardV2` + `GetAnalysisResponseV2` schema，增加 4 个字段；修改 `_build_decision_card` + 所有 `_build_*_result` 方法生成字段
2. **Phase 2（前端）：** 修改 `types.ts` 的 `DecisionCardV2` + `AnalysisDetail`；修改 `ResultPage.tsx` 新增两个证据展示区 + 置信度 Badge
3. **Phase 3（验证）：** TypeScript 编译 + Vite build + vitest 通过；手动 smoke（生成结果页同时包含四个新字段）

**回滚：** 只需 revert 后端 `analysis_generation_service.py` 和 schema 文件，前端未使用新字段时展示不受影响（字段被忽略）。

## Open Questions

**Q1:** `invalidation_conditions` 的条数是否固定为 3 条，还是根据场景动态生成？
→ **当前方案：** 固定 3 条（通用 2 条 + 场景特定 1 条），保证 UI 展示稳定性。

**Q2:** `confidence_level` 是否需要同时输出数值（0-100）？
→ **当前方案：** 暂只输出 `low/medium/high` 枚举。数值置信度在产品验证后再扩展，不在本次 scope。

**Q3:** 反方证据和失效条件是否需要与 `key_reason_summary` 一样有 `OutputMarkType` 标签？
→ **当前方案：** 不需要。这两个字段是结构化描述而非推理/事实分类，不适合用 `OutputMarkType` 标记。
