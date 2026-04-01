# AI 投资决策助手 JSON Schema Contract

更新时间：2026-03-30

## 1. 文档目的

本合同文档用于统一当前项目中关键 JSON 结构的字段定义、必填规则、枚举范围和示例。

目标是让以下角色使用同一份结构基线：

- 后端接口实现
- 前端状态映射
- 测试数据构造
- 数据库 JSONB 存储设计

## 2. 适用范围

当前优先覆盖以下 JSON 结构：

- `user_profile_snapshot`
- `scenario_payload`
- `analysis_results.user_fit_summary`
- `analysis_results.intervention`
- `analysis_results.market_context`
- `analysis_results.explanation_layer`
- `analysis_results.detail_panels`
- `review_tasks.attribution`
- 统一错误响应 `error`

## 3. 设计原则

- 所有 JSON 结构必须是稳定可解释的
- 能用明确字段表达的，不用模糊自由文本拼接
- 必填字段尽量少，但必须覆盖页面所需最小展示
- 枚举型字段必须统一口径
- 当前阶段优先保证结构清晰，不追求过度复杂

## 4. 通用枚举定义

### 4.1 通用业务枚举

`experience_level`

- `novice`
- `intermediate`
- `expert`

`holding_horizon`

- `short`
- `medium`
- `long`

`risk_tolerance`

- `low`
- `medium`
- `high`

`behavior_tag`

- `chasing_rise`
- `panic_sell`
- `frequent_trading`
- `stable_discipline`

`scenario`

- `single_stock_check`
- `pre_trade_check`
- `post_trade_review`

`analysis_status`

- `processing`
- `partial_ready`
- `ready`
- `expired`
- `failed`

`review_status`

- `pending`
- `completed`
- `expired`

`behavior_type`

- `chasing_rise`
- `panic_sell`
- `frequent_trading`

`severity`

- `low`
- `medium`
- `high`

`valid_period`

- `short`
- `medium`
- `long`

`degrade_flag`

- `missing_market_data`
- `missing_announcements`
- `model_fallback`
- `insufficient_evidence`

`pre_trade_intent`

- `buy`
- `add`
- `reduce`
- `sell`

`action_taken`

- `buy`
- `add`
- `reduce`
- `sell`

`intervention_action_taken`

- `continued`
- `delayed`
- `cancelled`
- `logged_only`

`attribution_score`

- `low`
- `medium`
- `high`

`data_source_key`

- `quote`
- `announcement`
- `profile_snapshot`
- `manual_input`

## 5. user_profile_snapshot

### 5.1 用途

- 存在于 `analysis_tasks.user_profile_snapshot`
- 用于锁定分析发生时的画像快照

### 5.2 结构定义

```json
{
  "experience_level": "novice",
  "holding_horizon": "medium",
  "risk_tolerance": "low",
  "behavior_tags": ["chasing_rise"],
  "profile_source": "user_input"
}
```

### 5.3 字段规则

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `experience_level` | string | 是 | 见通用枚举 |
| `holding_horizon` | string | 是 | 见通用枚举 |
| `risk_tolerance` | string | 是 | 见通用枚举 |
| `behavior_tags` | string[] | 是 | 元素来自 `behavior_tag` |
| `profile_source` | string | 是 | `user_input / default_conservative / imported` |

### 5.4 约束

- 不允许出现用户手机号、邮箱等身份字段
- `behavior_tags` 建议去重

## 6. scenario_payload

### 6.1 single_stock_check

```json
{
  "primary_horizon": "medium",
  "focus_reason": "关注估值和业绩稳定性"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `primary_horizon` | string | 否 | 见 `holding_horizon` |
| `focus_reason` | string | 否 | 建议 <= 500 |

### 6.2 pre_trade_check

```json
{
  "intent": "buy",
  "trigger_reason": "hot_topic",
  "emotion_level": 4,
  "original_plan": "回调后再观察"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `intent` | string | 是 | 见 `pre_trade_intent` |
| `trigger_reason` | string | 是 | 建议统一标签字典 |
| `emotion_level` | integer | 否 | `1-5` |
| `original_plan` | string | 否 | 建议 <= 500 |

### 6.3 post_trade_review

```json
{
  "action_taken": "sell",
  "trigger_reason": "panic_drop",
  "outcome_summary": "卖出后反弹",
  "emotion_level": 4,
  "plan_deviation": true
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `action_taken` | string | 是 | 见 `action_taken` |
| `trigger_reason` | string | 是 | 建议统一标签字典 |
| `outcome_summary` | string | 是 | 建议 <= 1000 |
| `emotion_level` | integer | 否 | `1-5` |
| `plan_deviation` | boolean | 否 | 是否偏离原计划 |

## 7. user_fit_summary

### 7.1 用途

- 对应 `analysis_results.user_fit_summary`
- 供结果页“适不适合我”区域使用

### 7.2 结构定义

```json
{
  "fit": "适合中期持有、风险偏好较低的用户参考",
  "unfit": "不适合短线冲动交易场景"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `fit` | string | 是 | 用户可读文本 |
| `unfit` | string | 是 | 用户可读文本 |

## 8. intervention

### 8.1 用途

- 对应 `analysis_results.intervention`
- 用于结果页行为干预卡

### 8.2 结构定义

```json
{
  "behavior_type": "chasing_rise",
  "severity": "high",
  "questions": [
    "这次动作是否偏离原计划？",
    "如果今天不操作，会失去什么？"
  ],
  "cooldown_minutes": 10,
  "trigger_reason": "hot_topic"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `behavior_type` | string | 是 | 见 `behavior_type` |
| `severity` | string | 是 | 见 `severity` |
| `questions` | string[] | 是 | 建议 1-5 条 |
| `cooldown_minutes` | integer | 否 | 正整数 |
| `trigger_reason` | string | 否 | 触发来源标签 |

## 9. market_context

### 9.1 用途

- 对应 `analysis_results.market_context`
- 用于市场背景卡

### 9.2 结构定义

```json
{
  "market_event": "近期板块波动较大",
  "impact_boundary": "仅说明短期情绪影响，不代表趋势判断",
  "data_sources": ["quote", "announcement"]
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `market_event` | string | 是 | 用户可读文本 |
| `impact_boundary` | string | 是 | 明确边界说明 |
| `data_sources` | string[] | 否 | 元素来自 `data_source_key` |

## 10. explanation_layer

### 10.1 用途

- 对应 `analysis_results.explanation_layer`
- 供 AI 解释抽屉使用

### 10.2 结构定义

```json
{
  "plain_text": "用更通俗的话解释当前判断",
  "case_example": "类似先观察再验证，而不是立即行动"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `plain_text` | string | 是 | 更通俗解释 |
| `case_example` | string | 是 | 场景类比 |

## 11. detail_panels

### 11.1 用途

- 对应 `analysis_results.detail_panels`
- 供详细推理区和测试核对使用

### 11.2 结构定义

```json
{
  "facts": ["估值水平处于历史中位附近"],
  "inferences": ["当前更适合等待更多验证信号"],
  "uncertainties": ["近期公告覆盖不完整"],
  "data_sources": ["quote", "announcement", "profile_snapshot"],
  "degrade_flags": ["missing_announcements"]
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `facts` | string[] | 是 | 事实列表 |
| `inferences` | string[] | 是 | 推理列表 |
| `uncertainties` | string[] | 是 | 不确定项列表 |
| `data_sources` | string[] | 是 | 元素来自 `data_source_key` |
| `degrade_flags` | string[] | 否 | 元素来自 `degrade_flag` |

## 12. attribution

### 12.1 用途

- 对应 `review_tasks.attribution`
- 用于复盘归因

### 12.2 结构定义

```json
{
  "judgement_quality": "medium",
  "execution_quality": "low",
  "luck_factor": "medium",
  "summary": "主要问题在执行而非初始判断"
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `judgement_quality` | string | 是 | 见 `attribution_score` |
| `execution_quality` | string | 是 | 见 `attribution_score` |
| `luck_factor` | string | 是 | 见 `attribution_score` |
| `summary` | string | 否 | 建议 <= 500 |

## 13. error

### 13.1 用途

- 统一接口错误响应结构

### 13.2 结构定义

```json
{
  "error": {
    "code": "ANALYSIS_TIMEOUT",
    "message": "本次分析未能完整完成，请稍后重试",
    "request_id": "req_xxx",
    "retryable": true
  }
}
```

字段规则：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `code` | string | 是 | 统一错误码 |
| `message` | string | 是 | 用户可读错误信息 |
| `request_id` | string | 是 | 便于追踪 |
| `retryable` | boolean | 是 | 是否建议重试 |

## 14. 联调要求

后端实现要求：

- 接口返回结构不得随意增删核心字段
- 新增字段必须先补本合同文档

前端实现要求：

- 仅基于本合同定义的字段消费数据
- 不得依赖未声明的临时字段

测试要求：

- 用例数据优先基于本合同构造
- 异常场景需覆盖必填缺失、枚举非法、类型错误

## 15. 最终结论

这份 JSON Contract 的作用，是把“大家口头知道这些 JSON 差不多长什么样”升级为“团队明确知道这些 JSON 必须长什么样”。

后续无论接口实现、数据库存储、前端渲染还是测试构造，都应以本文件为准。
