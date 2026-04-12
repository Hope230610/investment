## Why

当前真实代码仍存在以下问题：未认证业务访问会被开发态便利逻辑放行、运行时测试身份会被隐式注入、生产关键安全配置仍允许默认值兜底。这些行为与 `auth-session`、`platform-contracts` 已定义的共享访问边界和安全治理底线冲突。必须先收紧真实环境门槛，才能为后续 API 契约收口和联调提供稳定前提。

## What Changes

- 强化 `auth-session`，明确受保护业务访问必须 fail-closed。未认证请求、无效会话或隐式测试身份不得继续进入业务处理流程。
- 强化 `auth-session`，要求生产与真实内测环境在启动时显式拒绝任何绕过正式认证的便捷身份能力。
- 强化 `platform-contracts`，要求真实环境中的关键安全配置只能通过显式方式提供，不允许默认安全配置继续进入真实环境。
- 强化 `platform-contracts`，将未登录、会话失效、越权访问和日志脱敏要求纳入统一 contract，便于前后端与 QA 使用同一套基线验收。

## Capabilities

### New Capabilities

### Modified Capabilities
- `auth-session`: 收紧共享访问边界与真实环境隔离 requirements，明确 fail-closed 与启动门槛。
- `platform-contracts`: 收紧共享错误响应与安全治理 requirements，明确真实环境配置与日志脱敏约束。

## Impact

- 关联基线文档：`structure/investment_auth_and_authorization_design.md`、`structure/investment_security_and_data_governance_minimum_plan.md`、`structure/investment_api_contract_and_implementation_alignment.md`、`structure/investment_current_implementation_gap_audit.md`
- 受影响执行板泳道：后端负责人 `TASK-BE-001`、`TASK-BE-002`、`TASK-BE-003`、`TASK-BE-007`、`TASK-BE-010`；前端负责人 `TASK-FE-004`、`TASK-FE-005`；测试负责人 `TASK-QA-003`
- 受影响代码区域：`investment-back/src/api/deps.py`、`investment-back/main.py`、`investment-back/src/core/config.py`、`investment-back/src/api/*`、`investment-front/src/api.ts`、前端登录态与错误处理相关页面或状态层
