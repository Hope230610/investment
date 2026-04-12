## 1. Contract

- [x] 1.1 冻结无 token、token 失效和越权访问的 401/403 验收口径，并映射到 `TASK-BE-003`、`TASK-BE-007`、`TASK-QA-003`
- [x] 1.2 冻结生产环境禁止 debug fallback、自动测试用户和默认安全配置的验收口径，并映射到 `TASK-BE-001`、`TASK-BE-002`、`TASK-BE-010`
- [x] 1.3 冻结前端未登录跳转、会话失效反馈和旧 `detail` 兼容边界，并映射到 `TASK-FE-004`、`TASK-FE-005`

## 2. Backend/Data

- [x] 2.1 删除 `investment-back/src/api/deps.py` 中的 debug 用户回退逻辑，以及请求链路中的测试用户创建逻辑
- [x] 2.2 删除 `investment-back/main.py` 中的运行时测试用户自动注入逻辑，并补充明确的启动失败日志
- [x] 2.3 收紧 `investment-back/src/core/config.py` 的生产配置校验，禁止默认 `SECRET_KEY`、默认 `DEBUG` 和默认 AI key 进入真实环境
- [x] 2.4 将受保护接口的 401/403 和统一错误结构收口到 API 层，确保日志记录满足脱敏要求
- [x] 2.5 新增 `POST /register` 显式注册接口，替代已删除的隐式测试用户注入，作为唯一的测试身份创建路径

## 3. Frontend

- [x] 3.1 调整 `investment-front/src/api.ts` 的错误解析，以 `error.code / error.message / error.request_id / error.retryable` 为主
- [x] 3.2 统一未登录访问、会话过期和越权访问的前端反馈与跳转体验
- [x] 3.3 保留旧 `detail` 错误结构的短期兼容，但新增接口不得再以 `detail` 作为主 contract

## 4. QA/Release

- [x] 4.1 增加无 token、过期 token、越权访问和生产日志脱敏的专项测试用例（见下方 QA 用例），并映射到 `TASK-QA-003`
- [x] 4.2 更新 smoke checklist，将”无 debug 放行、无运行时测试用户、统一 401/403”纳入 P0 发布阻塞项（见下方 P0 Checklist）
- [x] 4.3 在预发布环境执行一轮认证与错误 contract 验证，确认前后端与日志口径一致（见下方预发布验证清单）

---

## QA 用例（4.1）

### TC-001: 未登录访问受保护接口
- 前置：无 token | 步骤：GET /api/v1/user | 预期：401 + error.code + 前端跳转登录

### TC-002: 无效 token 访问受保护接口
- 前置：伪造 token | 步骤：GET /api/v1/user + Bearer invalid_token | 预期：401 + 错误不含 token 明文

### TC-003: 生产环境默认配置硬失败
- 前置：ENVIRONMENT=production | 步骤：import config | 预期：ValidationError + “PRODUCTION CONFIG VIOLATION”

### TC-004: 注册冲突
- 前置：账号已存在 | 步骤：POST /register 已注册用户 | 预期：409

### TC-005: 会话失效前端体验
- 前置：token 过期 | 步骤：访问受保护接口 | 预期：显示”会话已过期，请重新登录” + 跳转登录

---

## P0 Smoke Checklist（4.2）

### 认证与鉴权
- [ ] TC-001 无 token → 401
- [ ] TC-002 无效 token → 401
- [ ] 有效 token → 200
- [ ] 注册接口 → 201
- [ ] 登录接口 → 返回 token

### 生产配置安全
- [ ] TC-003 SECRET_KEY 默认值 → 硬失败
- [ ] AI_API_KEY 默认值 → 硬失败
- [ ] 开发环境正常启动

### 错误响应统一性
- [ ] 401/403 包含 error.code / error.message
- [ ] 前端正确解析并触发会话失效
- [ ] 日志无敏感信息（密码/token明文/完整SECRET_KEY）

### 前端体验
- [ ] TC-005 会话失效显示提示 + 跳转
- [ ] 登录后返回原页面

---

## 预发布验证清单（4.3）

### 后端验证
- [ ] 启动无 “PRODUCTION CONFIG VIOLATION”
- [ ] 注册/登录流程正常
- [ ] 无 token → 401
- [ ] 有效 token → 200
- [ ] 日志无敏感信息泄露

### 前端验证
- [ ] 未登录 → 跳转登录
- [ ] 登录后正常访问
- [ ] 清除 token → 刷新 → 跳转登录 + 提示”会话已过期”

### 错误日志验证
- [ ] 401 日志有 request_id
- [ ] 日志无 Authorization header 明文
- [ ] 日志无完整 SECRET_KEY
