# p2-evidence-card: 结果页证据化（实施记录）

## Purpose

本 tasks.md 是 `p2-evidence-card` 变更的完整实施检查表，对应 `proposal.md` 的变更范围和 `design.md` 的技术决策。

## 1. Contract

- [x] 1.1 `p2-evidence-card` delta spec（`specs/single-stock-analysis/spec.md`）：更新 baseline `Requirement: 单股咨询结果必须输出六段式决策卡`，扩展字段清单和验收标准

## 2. Backend

- [x] 2.1 `schemas/analysis.py` — `DecisionCardV2` 新增 4 个字段：
  - `supporting_evidence: List[str]` — 支撑证据列表
  - `counter_evidence: List[str]` — 反方证据列表
  - `invalidation_conditions: List[str]` — 失效条件列表
  - `confidence_level: Literal["low", "medium", "high"]` — 置信度等级
- [x] 2.2 `schemas/analysis.py` — `GetAnalysisResponseV2` 在 `DecisionCardV2` 嵌套处透传新字段（Python Pydantic 自动透传嵌套模型字段）
- [x] 2.3 `services/analysis_generation_service.py` — `_build_decision_card` 增加 `confidence_level` 参数，基于 metrics 计算：
  ```
  if data_completeness <= 1: confidence = 'low'
  elif risk_score >= 3: confidence = 'low'
  elif risk_score >= 2 or data_completeness == 2: confidence = 'medium'
  else: confidence = 'high'
  ```
- [x] 2.4 `services/analysis_generation_service.py` — `_build_decision_card` 增加 `supporting_evidence` 生成：
  - 从 `key_reason_summary` 中提取 `DATA_FACT` 类型的前 3 条作为支撑证据
  - 格式化：`[支撑] {内容}`
- [x] 2.5 `services/analysis_generation_service.py` — `_build_decision_card` 增加 `counter_evidence` 生成：
  - `risk_score >= 2` → "如果「{风险事件}」相关风险兑现，判断方向可能需要重新评估"
  - `risk_score >= 2` → "当前判断建立在已知信号上，若新的不利信息出现，结论方向可能反转"
  - `data_completeness <= 1` → "数据信息不足，当前方结论的可靠性有限，不宜过度依赖"
  - 其他通用反方："短期催化剂消失或市场环境变化时，当前逻辑需重新评估"、"结论有效期过后，判断应重新生成，不建议长期沿用"
- [x] 2.6 `services/analysis_generation_service.py` — `_build_decision_card` 增加 `invalidation_conditions` 生成（固定 3 条）：
  - "超过结论有效期（{valid_until}）"
  - "出现监管问询、风险提示、减持公告或重大不利事件"
  - "价格出现放量异动（涨跌幅超过 ±5%）或原有趋势发生逆转"
- [x] 2.7 `services/analysis_generation_service.py` — 所有 `_build_*_result` 方法（`_build_single_stock_result`、`_build_pre_trade_result`、`_build_post_trade_result`、`_build_insufficient_data_result`）调用 `_build_decision_card` 时传入新参数

## 3. Frontend

- [x] 3.1 `types.ts` — `DecisionCardV2` 接口新增 4 个字段（与后端对齐）
- [x] 3.2 `types.ts` — `AnalysisDetail` 接口在 `decision_card` 嵌套中确认包含新字段（`DecisionCardV2` 已更新）
- [x] 3.3 `ResultPage.tsx` — 在"核心理由"（`key_reason_summary`）section 之后，新增**支撑证据** section：
  - 标题："支撑证据"（绿色 emerald 配色）
  - 每条前加 `S{index+1}` 前缀
  - 只展示前 3 条
- [x] 3.4 `ResultPage.tsx` — 新增**反方证据** section：
  - 标题："反方证据"（红色 red 配色）
  - 每条前加 `C{index+1}` 前缀
  - 与支撑证据明确分区
- [x] 3.5 `ResultPage.tsx` — 在 headline 区域新增**置信度 Badge**：
  - `high` → 绿色 "高置信"
  - `medium` → 黄色 "中置信"
  - `low` → 红色 "低置信"
  - 位置：headline 右上角；user_fit_summary 区域从 2 列改为 3 列，新增"置信等级"

## 4. QA

- [x] 4.1 TypeScript 编译零错误；Vite build 通过；vitest 46/46 全通过；后端 Python 导入正常；全链路 10/10 测试通过
- [x] 4.2 手动 smoke：
  - [x] 生成任意股票分析，决策卡同时包含 `counter_evidence` 和 `confidence_level`
  - [x] 低数据质量时置信度为 low（不能为 high）
  - [x] 支撑证据和反方证据展示区视觉明确区分
  - [x] 置信度 Badge 正确显示（高/中/低三种状态）
  - [x] `invalidation_conditions` 展示在"主要风险与失效条件"区域
