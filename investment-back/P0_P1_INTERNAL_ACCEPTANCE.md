# P0/P1 内测启动验收清单

目标：验证当前版本是否达到“可信可内测”，不覆盖 P2、商业化、完整持仓系统或复杂 AI 评测平台。

验收边界：
- Mock 行情 E2E 是日常回归基线，用于本地快速回归、CI 和普通改动合入前检查。
- 真实行情 E2E 是发布前验收基线，用于确认外部行情、公告数据和真实分析链路仍可用。
- 两种 E2E 都必须使用专用测试库，不得连接生产库或长期保留脏测试状态。
- 本清单只覆盖 P0/P1 内测可信度，不纳入 P2 持仓系统、组合盈亏/成本/仓位、商业化会员、社区分享、荐股列表、自动买卖点或复杂 AI 评测平台。

## 1. 后端基础守卫

```powershell
cd F:\investment\investment-back
python -m compileall src tests
pytest -q
```

验收标准：
- Python 语法编译通过。
- 后端回归测试全部通过。
- 不允许连接生产库执行会改数据的测试；需要显式设置 `RUN_DATA_MODIFYING_TESTS=1` 且使用测试库。

## 2. 前端基础守卫

```powershell
cd F:\investment\investment-front
npm run lint
npm run test -- --run
```

验收标准：
- TypeScript 类型检查通过。
- 前端单元测试通过。

## 3. 决策卡字段契约

GET `/api/v1/analysis/{analysis_id}` 的 `decision_card` 必须稳定包含：
- `supporting_evidence`
- `counter_evidence`
- `invalidation_conditions`
- `confidence_level`
- `confidence`
- `timestamp`
- `valid_until`

顶层响应也应包含：
- `timestamp`
- `valid_until`
- `data_as_of`

轮询中、失败、降级状态也必须返回结构完整的占位卡，不应因为缺字段导致结果页 500 或白屏。

## 4. 提醒中心验收

至少覆盖以下入口与类型：
- 首页 `/` 出现“今日关注”入口和摘要。
- 提醒中心 `/notifications` 可打开。
- `review_reminder`：复盘提醒。
- `watchlist_alert`：观察池异动。
- `analysis_invalidation`：分析失效提醒。

提醒接口失败时前端应显示可重试空状态，不影响首页主流程。

## 5. Learning Feedback 闭环

验收路径：
- 交易后复盘提交 Learning Feedback。
- 写入 `emotion_history` 与 `judgment_history`。
- `UserLearningService.compute()` 聚合为 `LearningMetrics`。
- `AdaptationService.adapt_decision_for_user()` 能在空数据和有数据时都返回可用决策卡。

空数据兜底：
- `judgment_avg=50.0`
- `emotion_avg=3.0`
- `judgment_trend_direction=stable`
- 不触发高情绪、判断下滑、频繁交易信号。

## 6. 失败兜底验收

必须验证：
- 股票标识无效时返回统一错误结构，不进入分析创建流程。
- 行情/外部数据不可用时返回可重试错误或低置信降级结果。
- 分析任务处理中和失败时，结果查询仍返回 schema 完整响应。
- 输出不得包含确定性买卖表达，例如“必须买入”“稳赚”“明天一定涨”。

## 7. Playwright E2E 验收流程

### 7.1 前置依赖

完整 E2E 不是纯前端测试，会真实启动前后端并写入测试库。

真实行情模式必须准备：
- PostgreSQL 可用。
- `DATABASE_URL` 指向专用测试库，不要指向生产库。
- 后端以 `DEBUG=true`、`ENVIRONMENT=development` 启动，确保 debug seed 接口可用。
- 测试账号存在：默认 `testuser / testpassword123`。
- 机器能访问外部行情接口；单条真实分析通常需要 20 到 60 秒。
- 端口默认占用：后端 `8000`，前端 `3000`。

Mock 行情模式额外设置：
- `E2E_MOCK_MARKET=true`
- `MOCK_MARKET_DATA=true`
- 适合 CI 和快速回归，不访问外部行情接口。

推荐 `.env`：

```powershell
# investment-back\.env
DEBUG=true
ENVIRONMENT=development
DATABASE_URL=postgresql://postgres:123456@localhost:5432/investment_test
SECRET_KEY=e2e-local-secret
AI_API_KEY=sk-e2e-placeholder
RQ_ASYNC=true
BACKEND_CORS_ORIGINS=["http://localhost:3000"]
# Mock 行情模式才需要：
E2E_MOCK_MARKET=true
MOCK_MARKET_DATA=true

# investment-front\.env
E2E_BASE_URL=http://localhost:3000
E2E_API_URL=http://localhost:8000
E2E_USER=testuser
E2E_PASS=testpassword123
BACKEND_BASE_URL=http://localhost:8000
```

### 7.2 测试库 reset/seed

推荐使用专用测试库，例如 `investment_e2e`。准备脚本会拒绝在非测试库运行：必须满足 `DEBUG=true`、`ENVIRONMENT=development/test/e2e`，且数据库名包含 `test` 或 `e2e`。

默认 reset/seed 语义：
- 未传 `--skip-reset` 时，`prepare_e2e_db.py` 会重建测试库 `public` schema，并重新 seed 测试账号、基础股票和用户画像，适合完整 E2E 前使用。
- 传入 `--skip-reset` 时，只补齐 schema、账号和基础股票，不清理已有 analysis、review、learning、watchlist 等状态，适合临时补数据，不作为发布前验收推荐路径。
- 一键验收脚本传入 `-PrepareDb` 时使用默认 reset/seed 路径，不传 `--skip-reset`。

一键准备测试库、测试账号和基础股票：

```powershell
cd F:\investment\investment-back
$env:DEBUG="true"
$env:ENVIRONMENT="development"
$env:DATABASE_URL="postgresql://postgres:123456@localhost:5432/investment_e2e"
python scripts/prepare_e2e_db.py --username testuser --password testpassword123
```

脚本会：
- 自动创建配置的 PostgreSQL 数据库（如不存在）。
- 默认重建该测试库的 `public` schema，然后用当前 SQLAlchemy models 创建 schema，用于清理半初始化/脏 schema。
- 确保 `testuser / testpassword123` 可登录。
- upsert E2E 所需股票：`SH600519`、`SZ002594`、`SZ300750`、`SH600036`、`SZ000001`、`SH601012`、`SH600900`。
- 清理测试库中的旧 schema 后重建，因此 analysis、review、learning、behavior intervention、watchlist、user action 等可变状态都会回到干净基线。
- 重置该测试用户画像为新手、中周期、中风险、空行为标签。

如果只想补齐账号和股票、不清理状态：

```powershell
python scripts/prepare_e2e_db.py --username testuser --password testpassword123 --skip-reset
```

`--skip-reset` 不会重建 schema，只补齐当前 SQLAlchemy models、账号 upsert 和股票 upsert；如果测试库已经半初始化，先不要使用 `--skip-reset`。

如果不使用准备脚本，也可以先启动后端后手动注册：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/v1/user/register `
  -ContentType "application/json" `
  -Body '{"username":"testuser","password":"testpassword123"}'
```

如果返回 `409 USERNAME_EXISTS`，表示账号已存在，可以继续。

### 7.3 手动启动方式

后端：

```powershell
cd F:\investment\investment-back
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Mock 行情后端：

```powershell
cd F:\investment\investment-back
$env:E2E_MOCK_MARKET="true"
$env:MOCK_MARKET_DATA="true"
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

前端：

```powershell
cd F:\investment\investment-front
$env:BACKEND_BASE_URL="http://localhost:8000"
npm run dev
```

健康检查：

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/ready
Invoke-WebRequest -UseBasicParsing http://localhost:3000
```

### 7.4 E2E 命令

枚举用例：

```powershell
cd F:\investment\investment-front
npm run --silent test:e2e -- --list
```

运行单条冒烟：

```powershell
cd F:\investment\investment-front
npm run --silent test:e2e -- tests/e2e/analysis-pipeline.spec.ts:33 --workers=1 --timeout=120000
```

运行完整 E2E：

```powershell
cd F:\investment\investment-front
npm run --silent test:e2e
```

说明：
- Playwright 配置会自动启动后端和前端，也会复用已存在服务。
- `fullyParallel=false`、`workers=1` 是有意设置，因为测试会写 learning history、profile tags、review task。
- 完整 21 条用例在真实行情环境下约 12 分钟，不应使用 4 分钟以内的外层超时判断失败。
- 如果切换 Mock/真实行情模式，建议停止已有 `8000/3000` 服务，避免 Playwright 复用旧服务。

### 7.5 一键验收脚本

轻量脚本位置：

```powershell
F:\investment\investment-front\scripts\run-e2e-acceptance.ps1
```

脚本固定执行顺序：
1. 后端 `python -m compileall src tests scripts`
2. 后端 `pytest -q`
3. 可选 `-PrepareDb`：reset/seed E2E 测试库
4. 前端 `npm run lint`
5. 前端 `npm run test -- --run`
6. 前端 `npm run build`
7. Playwright `--list`
8. 可选 `-Full`：完整 Playwright E2E

只跑基础守卫和 E2E 枚举：

```powershell
cd F:\investment\investment-front
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -ListOnly
```

Mock 行情完整验收（推荐 CI / 快速回归）：

```powershell
cd F:\investment\investment-front
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full
```

验收定位：这是日常回归推荐命令。它应稳定、可复现、不访问外部行情接口，适合每次 P0/P1 收口改动后运行。

真实行情完整验收（更接近真实环境，但慢且依赖网络）：

```powershell
cd F:\investment\investment-front
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 -PrepareDb -Full
```

验收定位：这是发布前验收推荐命令。它用于确认真实行情/公告接口、后端分析链路和前端轮询展示在真实数据条件下可用；不建议作为每次日常开发的唯一回归依据。

可显式指定测试库：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-e2e-acceptance.ps1 `
  -PrepareDb `
  -MockMarket `
  -Full `
  -DatabaseUrl "postgresql://postgres:123456@localhost:5432/investment_e2e"
```

### 7.6 两种验收模式

- Mock 行情模式：设置 `E2E_MOCK_MARKET=true` 或 `MOCK_MARKET_DATA=true` 后启用，后端 service 层返回固定 A 股测试数据。它是日常回归基线，优点是稳定、可复现、不访问外网，适合 CI；缺点是不验证第三方行情可用性。
- 真实行情模式：默认模式，使用 `MarketDataService` 访问外部行情/公告接口。它是发布前验收基线，优点是贴近真实产品，缺点是慢、依赖网络和第三方接口。

### 7.7 常见失败原因

- prepare 脚本拒绝执行：当前数据库名不含 `test/e2e`，这是保护机制。换用 `investment_e2e` 或显式 `-DatabaseUrl`。
- 后端未启动：`http://localhost:8000/health` 不通。
- 数据库不可用：`http://localhost:8000/ready` 返回 503。
- 测试用户缺失：登录页停留或 `/api/v1/user/login` 返回 `INVALID_CREDENTIALS`。
- 前端代理不一致：前端请求 `/api/*` 失败，确认 `BACKEND_BASE_URL`。
- 外部行情慢或失败：分析轮询超过 60 秒，先单跑对应用例确认是否偶发。
- Mock 模式仍访问真实行情：确认后端不是复用旧进程；停止 8000 端口服务后重跑。
- UI 与 API 轮询竞争：测试 helper 会在 API ready 后等待结果页同步渲染，若仍失败，优先查看 `test-results/*/error-context.md`。
- 共享状态污染：完整 E2E 使用同一测试用户并写入学习历史；如果本地反复跑后异常，重建测试库或换一个 `E2E_USER`。

### 7.8 当前已知未解决问题

- 真实行情模式仍依赖外部接口，速度和稳定性受网络影响。
- Vite build 有 chunk 超 500KB 提示，不影响内测启动，但后续可做代码分割。
