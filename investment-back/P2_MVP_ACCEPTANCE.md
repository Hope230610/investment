# P2 MVP 验收记录

日期：2026-05-04

## P2 MVP 范围

- 新增手动维护的持仓快照：成本价、数量、当前价、浮动盈亏、持仓占比、更新时间。
- 新增交易流水：买入/卖出、价格、数量、时间、交易理由，可关联分析/自检/复盘。
- 新增组合概览：总市值估算、总盈亏、最大单票占比、集中度提醒、风险提示。
- 分析任务创建时写入当前用户的持仓上下文，结果页展示持仓背景。
- 提醒中心聚合当前用户的持仓集中度和浮亏复盘提醒。
- 前端新增 `/portfolio` 页面，并接入底部导航、首页摘要和结果页持仓上下文展示。

## 本轮不做事项

- 不接券商账户。
- 不接真实资金账户。
- 不做自动交易。
- 不做荐股。
- 不输出确定性买卖建议。
- 不新增组合优化算法。
- 不由交易流水自动反推或自动调整持仓。

## 数据模型说明

- 迁移文件：`alembic/versions/012_add_portfolio_tables.py`。
- 新增表：`holdings`、`transactions`。
- 迁移只新增 P2 表、索引、外键和 `transactionside` 枚举，不删除或修改 P0/P1 既有表字段。
- `downgrade` 只删除 P2 新增索引、表和枚举。
- 持仓和流水均带 `user_id`，并建立用户维度索引；持仓包含 `user_id + stock_id` 唯一索引。
- 关键数量、价格字段使用 `Numeric(18, 4)` 存储，服务层输出时统一转换为前端消费的数值。

## API 说明

- `GET /api/v1/portfolio/holdings`：查询当前用户持仓。
- `POST /api/v1/portfolio/holdings`：新增或更新当前用户某标的持仓快照。
- `PUT /api/v1/portfolio/holdings/{holding_id}`：只更新当前用户持仓。
- `DELETE /api/v1/portfolio/holdings/{holding_id}`：只删除当前用户持仓。
- `GET /api/v1/portfolio/transactions`：查询当前用户交易流水，支持 `stock_id` 和受限 `limit`。
- `POST /api/v1/portfolio/transactions`：新增当前用户交易流水。
- `PUT /api/v1/portfolio/transactions/{transaction_id}`：只更新当前用户交易流水。
- `DELETE /api/v1/portfolio/transactions/{transaction_id}`：只删除当前用户交易流水。
- `GET /api/v1/portfolio/summary` / `overview`：只统计当前用户持仓。

## 前端页面说明

- `/portfolio` 包含 loading、empty、error、持仓列表、组合摘要、新增/编辑/删除持仓、交易流水录入、最近交易、更新时间和风险提示。
- 当前价格依赖用户手动维护，页面已明确提示可能不是实时价格。
- 结果页仅在存在持仓上下文时展示“当前持仓上下文”，并提示持仓价格更新时间和非实时边界。
- 底部导航新增“持仓”入口；为避免真实行情模式下提醒摘要聚合阻塞组合页首屏，`/portfolio` 不主动刷新提醒 badge。

## 与 P0/P1 闭环的关系

- P2 持仓上下文作为分析、自检、复盘和提醒的辅助事实背景。
- P2 不改变 P0/P1 的结论生成、证据结构、行为干预和复盘闭环语义。
- P2 不替代交易前自检和复盘记录，只帮助用户把仓位、浮亏和集中度纳入判断。

## AI 合规表达边界

- 禁止输出“立即买入”“必须卖出”“推荐满仓”“必涨”“稳赚”“无风险”“低风险高收益”“强烈推荐交易”等确定性交易表达。
- 允许输出“当前仓位偏高，建议重新核验证据”“当前浮亏可能影响情绪判断”“当前持仓集中度较高，需要关注组合风险”“若原始买入理由失效，应重新评估”等辅助提醒。
- 组合风险提示是规则型辅助提醒，不构成投资建议。
- 系统不会接入券商、不会代用户交易、不会给出买卖指令。

## 风险与限制

- 持仓依赖用户手动维护，可能滞后或录入错误。
- 当前价格可能不是实时价格。
- 交易流水是用户行为记录，本轮不自动汇总成持仓。
- 组合集中度和浮亏提醒是规则型提示，不代表收益预测。
- Redis/RQ 仍非本轮默认路径。
- P2 MVP 仍不是成熟生产态，需要后续补充权限/API 集成测试、迁移演练和性能观察。

## 实际测试命令与结果

```powershell
cd F:\investment\investment-back
python -m compileall src tests
# passed
pytest -q
# 79 passed, 119 warnings

cd F:\investment\investment-front
npm run lint
# passed
npm run test -- --run
# 50 passed
npm run build
# passed; existing chunk warning: index js > 500 kB
npx playwright test --list
# 22 tests listed
npx playwright test tests/e2e/portfolio.spec.ts
# 1 passed
./scripts/run-e2e-acceptance.ps1 -PrepareDb -MockMarket -Full
# 22 passed
./scripts/run-e2e-acceptance.ps1 -PrepareDb -Full
# 22 passed
```

## 本轮收口修复

- 将持仓/流水关键数值列从 `Float` 收口为 `Numeric(18, 4)`，并补齐 Decimal 序列化边界测试。
- 为交易流水列表 `limit` 增加范围校验。
- 为交易流水更新中的可选 UUID 字段补充校验，避免非法输入进入服务层。
- 为 `/portfolio` 增加首屏错误态。
- 为结果页持仓上下文补充价格更新时间和非实时说明。
- 为前端会话 bootstrap 增加超时兜底，避免会话校验请求挂起导致受保护页面无限 loading。
- 避免 `/portfolio` 首屏主动刷新提醒 badge，防止真实行情提醒聚合阻塞组合页加载。

## 已知问题

- 当前 P2 MVP 不接券商、不接真实资金账户、不做自动交易。
- 持仓需要用户手动维护，当前价可能不是实时价。
- 完整提醒聚合在真实行情模式下仍可能受第三方行情响应速度影响。
- 构建仍存在既有 500KB chunk warning。
- P2 仍需后续补充更系统的 API 权限隔离集成测试和数据库迁移演练。

## 后续建议

- 增加 Portfolio API 的 TestClient/DB 集成测试，覆盖跨用户 update/delete/list 隔离。
- 将提醒摘要接口改为真正轻量聚合，避免 Tab badge 依赖完整行情聚合。
- 补充 Alembic upgrade/downgrade 的独立迁移演练。
- 后续如要自动由流水汇总持仓，需另开变更并明确冲突处理规则。
