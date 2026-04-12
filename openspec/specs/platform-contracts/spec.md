## Purpose

定义跨场景共享的响应语义、状态口径、结果结构稳定性、降级表达和安全治理底线，作为前后端、数据层、测试和运营共同依赖的共享基线。本 spec 描述“跨能力必须一致的协议与治理规则”，不承担单个业务场景的产品语义。
## Requirements
### Requirement: 统一错误响应 contract
系统 SHALL 对业务错误、认证错误和系统错误使用统一错误响应结构：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "面向用户的可读文案",
    "request_id": "traceable-id",
    "retryable": true
  }
}
```

前后端 MUST 以 `error.code`、`error.message`、`error.request_id`、`error.retryable` 作为统一解析入口，不得继续依赖旧的 `detail` 风格字段。401 与 403 响应也 MUST 使用同一错误对象，以便前端与 QA 能统一消费未登录、会话失效和越权访问。

#### Scenario: 受保护接口返回 401
- **WHEN** 未登录用户访问受保护接口
- **THEN** 系统返回包含 `error.code`、`error.message`、`error.request_id`、`error.retryable` 的统一 401 错误结构

### Requirement: 统一分析与复盘状态枚举
系统 SHALL 对分析任务统一使用 `processing`、`partial_ready`、`ready`、`expired`、`failed` 状态枚举，对复盘任务统一使用 `pending`、`completed`、`expired` 状态枚举。当前后端、数据层、测试或运营文档表达同一生命周期状态时，MUST 使用同一组枚举口径和语义，不得为局部实现临时创造平行状态。

#### Scenario: 前端轮询分析任务状态
- **WHEN** 前端轮询某个分析任务
- **THEN** 返回值中的状态字段只使用约定枚举，而不出现临时字符串或未定义状态

### Requirement: 关键 JSON 结构必须稳定且可解释
系统 MUST 为用户画像快照、场景输入快照、适配摘要、行为干预、市场上下文、解释层、详情面板和复盘归因等关键结果对象提供稳定、可解释、可校验的结构化 contract。能够用明确字段和枚举表达的内容，SHALL 不通过自由文本拼接混入关键 contract。一旦某个关键对象对外发布，后续调整 MUST 以兼容演进为前提。

#### Scenario: 返回单股咨询结果详情
- **WHEN** 系统返回包含适配摘要、干预信息和解释层的分析结果
- **THEN** 相关 JSON 字段符合约定结构，并且枚举值与统一 contract 保持一致

### Requirement: 降级标记与安全输出边界必须统一
系统 SHALL 使用统一的 `degrade_flags` 表达降级原因，至少覆盖 `missing_market_data`、`missing_announcements`、`model_fallback`、`insufficient_evidence`。当任一降级标记影响核心判断时，系统 MUST 收敛结果文案和下一步动作，不得将降级输出伪装成完整结论。

#### Scenario: 模型调用失败但规则层可提供最低安全输出
- **WHEN** 分析流程中的模型调用失败，但规则层仍能给出最低安全结论
- **THEN** 系统返回带 `degrade_flags` 的降级结果，并限制输出为等待、复查或补充信息

### Requirement: 安全与数据治理最低要求
系统 MUST 满足最小安全与数据治理底线：生产环境不得启用默认测试账号、默认调试登录或默认可用密钥；敏感字段不得明文进入日志；用户只能访问自己的业务数据；高敏行为数据的导出、删除、留存和备份必须有明确规则。生产配置 SHALL 通过显式方式提供关键安全配置，并确保真实环境默认关闭调试类能力。若检测到默认安全配置、调试类能力或运行时测试身份注入能力仍被启用，系统 MUST 在启动阶段直接失败。

#### Scenario: 生产环境加载默认安全配置
- **WHEN** 应用在生产或真实内测环境启动，并检测到默认安全配置或调试类能力仍被启用
- **THEN** 系统拒绝继续启动，并记录可追踪但不泄露敏感值的错误日志

