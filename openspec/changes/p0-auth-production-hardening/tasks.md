## 1. Contract

- [ ] 1.1 冻结无 token、token 失效、越权访问的 401/403 验收口径，并映射到 `TASK-BE-003`、`TASK-BE-007`、`TASK-QA-003`
- [ ] 1.2 冻结生产环境禁止 debug fallback、自动测试用户和默认安全配置的验收口径，并映射到 `TASK-BE-001`、`TASK-BE-002`、`TASK-BE-010`
- [ ] 1.3 冻结前端未登录跳转、会话失效反馈和旧 `detail` 兼容边界，并映射到 `TASK-FE-004`、`TASK-FE-005`

## 2. Backend/Data

- [ ] 2.1 删除 `investment-back/src/api/deps.py` 中的 debug 用户回退与请求链路测试用户创建逻辑
- [ ] 2.2 删除 `investment-back/main.py` 中的运行时测试用户自动注入逻辑，并补明确的启动失败日志
- [ ] 2.3 收紧 `investment-back/src/core/config.py` 的生产配置校验，禁止默认 `SECRET_KEY`、默认 `DEBUG` 和默认 AI key 进入真实环境
- [ ] 2.4 将受保护接口的 401/403 与统一错误结构收口到 API 层，确保日志记录遵守脱敏要求

## 3. Frontend

- [ ] 3.1 调整 `investment-front/src/api.ts` 的错误解析，以 `error.code / error.message / error.request_id / error.retryable` 为主
- [ ] 3.2 统一未登录访问、会话过期和越权访问的前端反馈与跳转体验
- [ ] 3.3 保留旧 `detail` 错误结构的短期兼容，但新增接口不得再以 `detail` 作为主 contract

## 4. QA/Release

- [ ] 4.1 增加无 token、过期 token、越权访问、生产日志脱敏的专项测试用例，并映射到 `TASK-QA-003`
- [ ] 4.2 更新 smoke checklist，把“无 debug 放行、无运行时测试用户、统一 401/403”纳入 P0 发布阻塞项
- [ ] 4.3 在预发布环境执行一轮认证与错误 contract 验证，确认前后端与日志口径一致
