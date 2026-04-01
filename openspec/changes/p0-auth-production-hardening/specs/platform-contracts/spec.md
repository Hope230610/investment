## MODIFIED Requirements

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

前后端 MUST 以 `error.code`、`error.message`、`error.request_id`、`error.retryable` 作为统一解析入口，而不是继续依赖旧的 `detail` 风格字段。401 与 403 响应也 MUST 使用同一错误对象，以保证未登录、会话失效和越权访问可以被前端与 QA 统一消费。

#### Scenario: 受保护接口返回 401
- **WHEN** 未登录用户访问受保护接口
- **THEN** 系统返回包含 `error.code`、`error.message`、`error.request_id`、`error.retryable` 的统一 401 错误结构

### Requirement: 安全与数据治理最低要求
系统 MUST 满足最小安全与数据治理底线：生产环境不得启用默认测试账号、默认调试登录或默认可用密钥；敏感字段不得明文进入日志；用户只能访问自己的业务数据；高敏行为数据的导出、删除、留存和备份必须有明确规则。生产配置 SHALL 通过显式方式提供关键安全配置，并确保真实环境默认关闭调试类能力；若检测到默认安全配置、调试类能力或运行时测试身份注入能力仍被启用，系统 MUST 在启动阶段直接失败。

#### Scenario: 生产环境加载默认安全配置
- **WHEN** 应用在生产或真实内测环境启动，并检测到默认安全配置或调试类能力仍被启用
- **THEN** 系统拒绝继续启动，并记录可追踪但不泄露敏感值的错误日志
