# AI 投资决策助手 API 契约与实现收口文档

更新时间：2026-03-30

## 1. 文档目的

本方案用于把 PRD、UI 结构、数据库设计、类型定义和迁移文件中的实现口径统一起来。

本方案重点解决：

- 前后端接口字段是否一致
- 状态枚举是否一致
- 数据库设计与类型定义是否一致
- 当前文档中哪些地方已经出现冲突

## 2. 当前收口状态

### 2.1 已收口：数据库字符集表述

在 [database_design.md](F:/investment/structure/database_design.md) 中：

- 数据库类型写的是 PostgreSQL 15+
- 字符集却写成了 `UTF8MB4`

当前状态：

- 已统一改为 PostgreSQL `UTF8`
- [database_design.md](F:/investment/structure/database_design.md) 已同步修正

### 2.2 已收口：UUID 扩展口径

在 [001_init_schema.sql](F:/investment/structure/migrations/001_init_schema.sql) 中启用了：

- `uuid-ossp`

但默认值使用的是：

- `gen_random_uuid()`

当前状态：

- 已统一为 `pgcrypto + gen_random_uuid()`
- [migrations/001_init_schema.sql](F:/investment/structure/migrations/001_init_schema.sql) 已同步修正

### 2.3 已收口：测试用户与上线要求冲突

在 [002_init_data.sql](F:/investment/structure/migrations/002_init_data.sql) 中仍插入：

- `test@example.com`
- `demo@example.com`

当前状态：

- 测试用户已从 [migrations/002_init_data.sql](F:/investment/structure/migrations/002_init_data.sql) 移出
- 已新增 [migrations/004_dev_seed.sql](F:/investment/structure/migrations/004_dev_seed.sql) 作为开发/演示专用 seed
- [migrations/README.md](F:/investment/structure/migrations/README.md) 已同步更新生产与开发执行边界

### 2.4 仍需继续收口：状态与响应结构

当前文档中常见状态：

- `processing`
- `partial_ready`
- `ready`
- `expired`
- `failed`

当前建议：

- API 契约继续以 `status` 为主字段
- 降级场景通过 `degrade_flags` 补充表达
- 统一错误响应仍需在真实后端实现中落地

## 3. API 设计原则

- 前端只依赖 API 契约，不直接依赖数据库结构
- 返回字段优先服务页面展示，而不是直接回传表结构
- 所有错误响应统一
- 所有列表响应支持分页
- 所有状态字段必须使用明确枚举

## 4. 统一错误响应

建议所有错误响应统一为：

```json
{
  "error": {
    "code": "ANALYSIS_TIMEOUT",
    "message": "本次分析未能完整完成，请稍后重试",
    "request_id": "xxx",
    "retryable": true
  }
}
```

## 5. 核心 API 契约

### 5.1 用户画像

`GET /api/v1/user/profile`

响应：

```json
{
  "profile": {
    "experience_level": "novice",
    "holding_horizon": "medium",
    "risk_tolerance": "low",
    "behavior_tags": ["chasing_rise"],
    "profile_source": "user_input"
  }
}
```

`PUT /api/v1/user/profile`

请求：

```json
{
  "experience_level": "novice",
  "holding_horizon": "medium",
  "risk_tolerance": "low",
  "behavior_tags": ["chasing_rise"]
}
```

### 5.2 股票搜索

`GET /api/v1/stocks/search?q=xxx`

响应：

```json
{
  "items": [
    {
      "stock_id": "uuid",
      "stock_code": "600519",
      "stock_name": "贵州茅台",
      "market": "SH",
      "industry": "白酒"
    }
  ]
}
```

### 5.3 创建分析任务

`POST /api/v1/analysis`

请求：

```json
{
  "scenario": "pre_trade_check",
  "stock_id": "uuid",
  "scenario_payload": {
    "intent": "buy",
    "trigger_reason": "hot_topic",
    "emotion_level": 4
  }
}
```

响应：

```json
{
  "analysis_id": "uuid",
  "status": "processing",
  "estimated_ready_in_ms": 8000
}
```

### 5.4 获取分析结果

`GET /api/v1/analysis/:id`

响应：

```json
{
  "analysis_id": "uuid",
  "status": "ready",
  "degrade_flags": [],
  "decision_card": {
    "headline_judgement": "当前更适合继续观察，不宜快速下判断",
    "key_reason_summary": ["原因1", "原因2"],
    "user_fit_summary": {
      "fit": "适合中期持有者参考",
      "unfit": "不适合短线冲动交易场景"
    },
    "next_step_actions": ["等待下一次验证信号"],
    "primary_risks": "短期波动风险较高",
    "review_at": "2026-04-05T10:00:00Z"
  },
  "intervention": null,
  "fit_summary": "更适合中期风险承受较低的用户",
  "market_context": null,
  "explanation_layer": null,
  "detail_panels": null,
  "review_task": {
    "id": "uuid",
    "review_at": "2026-04-05T10:00:00Z",
    "status": "pending"
  }
}
```

### 5.5 历史记录

`GET /api/v1/records`

响应：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### 5.6 复盘任务

`GET /api/v1/reviews`

`POST /api/v1/reviews/:id/complete`

## 6. 枚举统一建议

### 6.1 Scenario

- `single_stock_check`
- `pre_trade_check`
- `post_trade_review`

### 6.2 Analysis Status

- `processing`
- `partial_ready`
- `ready`
- `expired`
- `failed`

### 6.3 Review Status

- `pending`
- `completed`
- `expired`

## 7. 数据库与 API 映射原则

- 数据库中的 `analysis_results` 不直接暴露给前端
- API 返回 `decision_card` 作为结果页主容器
- 数据库中的自由扩展字段保留在 `JSONB`
- 所有 JSONB 字段要有结构说明，不能无限散写

## 8. 当前仍需修正的实现项

### P0

- 在真实后端实现中统一错误响应格式
- 在真实接口实现中统一任务状态枚举
- 确保前后端实际响应结构与本契约一致

### P1

- 为所有列表接口补分页协议
- 为所有写接口补幂等和校验规则
- 为 `detail_panels`、`intervention`、`market_context` 补 JSON Schema

## 9. 结论

当前项目最缺的不是“更多接口”，而是“接口和实现口径统一”。

当前已经完成了数据库口径统一和测试/生产 seed 分离。

后续最关键的收口点，已经从“文档冲突”转向“真实接口实现是否遵守契约”。
