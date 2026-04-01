# AI 投资决策助手 当前实现差距审查

更新时间：2026-03-30

## 1. 文档目的

本审查用于对照 `structure` 中已经形成的产品落地文档体系，判断当前真实代码实现还存在哪些关键差距。

审查范围：

- `investment-back`
- `investment-front`
- 当前 Alembic 与模型实现

审查标准：

- 以 `structure` 中已经冻结的产品、架构、认证、异常、安全、API、数据库基线为准

## 2. 总体结论

当前项目已经具备“可演示、可跑通部分主链路”的基础，但仍明显停留在偏 MVP / demo 级实现状态，尚未真正对齐我们已经补齐的落地产品基线。

最突出的结论有四点：

1. 认证与身份边界尚未收口，仍存在开发态默认放行和自动创建测试用户逻辑
2. 后端数据模型仍是旧结构，和 `structure` 中定义的新数据库方案存在明显分叉
3. API 与前端消费结构仍是旧契约，尚未切换到新的统一 contract
4. 安全与配置底线未满足，存在默认密钥和默认 AI key 直写配置的问题

## 3. P0 Findings

### 3.1 开发态身份放行仍然存在

严重级别：P0

位置：

- [deps.py](F:/investment/investment-back/src/api/deps.py)

问题：

- `get_current_user()` 在 `DEBUG` 下如果没有 token，会直接返回 debug 用户
- `_get_or_create_debug_user()` 还会在请求路径中动态创建测试用户

为什么危险：

- 这直接违反了 [investment_auth_and_authorization_design.md](F:/investment/structure/investment_auth_and_authorization_design.md) 中“无 token 不得放行”的基线
- 也会导致测试数据与真实数据混入

建议：

- 彻底移除 debug fallback
- dev/test 环境改用显式测试登录，不允许隐式放行

### 3.2 启动时仍自动创建测试用户

严重级别：P0

位置：

- [main.py](F:/investment/investment-back/main.py)

问题：

- `startup_event()` 中如果用户表为空，会自动创建 `test@example.com` 与测试画像

为什么危险：

- 这与 [migrations/002_init_data.sql](F:/investment/structure/migrations/002_init_data.sql) 已经收口后的生产 seed 策略冲突
- 会让运行时再次把生产与开发数据混写

建议：

- 删除运行时自动 seed
- 只保留显式执行的 dev seed

### 3.3 默认安全配置不达标

严重级别：P0

位置：

- [config.py](F:/investment/investment-back/src/core/config.py)

问题：

- `SECRET_KEY` 仍有默认值
- `DEBUG` 默认是 `True`
- `AI_API_KEY` 直接带默认值

为什么危险：

- 这违反了 [investment_security_and_data_governance_minimum_plan.md](F:/investment/structure/investment_security_and_data_governance_minimum_plan.md) 中的最小安全底线
- 也不符合真实内测/灰度环境的配置要求

建议：

- 生产环境强制要求环境变量提供密钥
- 默认 `DEBUG=False`
- 不允许把真实密钥或默认可用 key 写在配置默认值里

### 3.4 后端核心数据模型仍是旧表结构

严重级别：P0

位置：

- [analysis.py](F:/investment/investment-back/src/models/analysis.py)
- [user.py](F:/investment/investment-back/src/models/user.py)
- [001_init_schema.py](F:/investment/investment-back/alembic/versions/001_init_schema.py)

问题：

- 当前后端仍使用：
  - `analyses`
  - `analysis_reasons`
  - `watchlist_items`
  - `focus_reasons`
- 用户和画像模型也仍是旧字段体系，比如：
  - `username`
  - `investment_goals`
  - `portfolio_size`
  - `preferred_sectors`

而 `structure` 的新基线已经定义为：

- `analysis_tasks`
- `analysis_results`
- `watchlists`
- `user_actions`
- `system_configs`
- 更收口的画像字段与 JSON 结构

为什么危险：

- 这意味着当前代码和当前文档已经是两套系统，不是一个系统的不同阶段
- 如果不先选定目标结构，继续开发会让后续迁移成本暴涨

建议：

- 明确以后端重构到新结构为目标
- 不再在旧 `analyses` 模型上继续叠加复杂逻辑

## 4. P1 Findings

### 4.1 API 结构仍是旧版本，未对齐新 contract

严重级别：P1

位置：

- [analysis.py](F:/investment/investment-back/src/api/v1/analysis.py)
- [analysis.py](F:/investment/investment-back/src/schemas/analysis.py)
- [types.ts](F:/investment/investment-front/src/types.ts)

问题：

- 当前 API 和前端类型仍围绕旧的 `Analysis / AnalysisWithDetails / DecisionCard` 结构
- 还没有切换到 [investment_json_schema_contract.md](F:/investment/structure/investment_json_schema_contract.md) 和 [investment_api_contract_and_implementation_alignment.md](F:/investment/structure/investment_api_contract_and_implementation_alignment.md) 中的新 contract 表达

例子：

- 后端 `BehaviorIntervention.severity` 仍是宽泛字符串
- `MarketContext` 仍带 `tag` 字段，而新 contract 已更偏向 `data_sources`
- `AnalysisStatus` 在前端仍缺少 `partial_ready`

建议：

- 先冻结真实 v1 contract
- 再统一改后端 schema 与前端类型

### 4.2 前端错误解析仍按旧 `detail` 风格处理

严重级别：P1

位置：

- [api.ts](F:/investment/investment-front/src/api.ts)

问题：

- `toErrorMessage()` 仍优先读取 `detail`
- 这和新文档中的统一错误响应：
  - `error.code`
  - `error.message`
  - `error.request_id`
  - `error.retryable`
  不一致

建议：

- 前端请求层切到新错误 contract
- 同时兼容旧接口一段过渡期

### 4.3 前端状态枚举未对齐

严重级别：P1

位置：

- [types.ts](F:/investment/investment-front/src/types.ts)

问题：

- `AnalysisStatus` 仍是：
  - `processing`
  - `ready`
  - `expired`
  - `failed`

缺少：

- `partial_ready`

并且没有显式 `degrade_flags`

建议：

- 与 [db_types.ts](F:/investment/structure/db_types.ts) 和 JSON contract 对齐

### 4.4 后端仍采用同步背景任务模型，未真正走异步 worker 边界

严重级别：P1

位置：

- [analysis.py](F:/investment/investment-back/src/api/v1/analysis.py)

问题：

- 当前使用 `BackgroundTasks` 直接在 API 进程里执行分析
- 这还不是 [investment_production_system_architecture.md](F:/investment/structure/investment_production_system_architecture.md) 所要求的异步任务边界

建议：

- 当前阶段至少把“分析任务创建”和“分析执行”在代码结构上拆开
- 后续替换为真实 Worker / Queue

## 5. P2 Findings

### 5.1 前端导航中仍保留观察列表入口

严重级别：P2

位置：

- [App.tsx](F:/investment/investment-front/src/App.tsx)

问题：

- 当前底部导航仍有“观察”入口
- 但文档里对观察列表的策略是“需评估是否保留、弱化或隐藏”

建议：

- 等产品负责人先冻结观察列表策略，再决定是否继续保留一级入口

### 5.2 旧字段仍在前端类型中保留

严重级别：P2

位置：

- [types.ts](F:/investment/investment-front/src/types.ts)

问题：

- 仍有不少旧结构字段，例如：
  - `investment_goals`
  - `portfolio_size`
  - `preferred_sectors`

而当前产品基线里这些字段已经不是 v1 最小画像的一部分

建议：

- 类型层同步收口
- 不再让前端页面依赖这些旧字段

## 6. 当前实现与基线的匹配度判断

### 6.1 已经较接近的部分

- 前端页面骨架已存在
- 后端已有基本 API 分层
- 登录、分析、记录、复盘的概念链路已经有雏形
- 前后端都已具备进一步重构的基础

### 6.2 明显未对齐的部分

- 认证边界
- 生产配置安全性
- 数据模型命名和结构
- API 契约
- 错误响应
- 状态枚举
- 任务执行架构

## 7. 建议的修复顺序

### 第一步

- 关掉 debug 放行和启动自动测试用户
- 修掉默认密钥与默认 AI key

### 第二步

- 冻结真实后端目标数据模型
- 决定是否从旧 `analyses` 迁移到新 `analysis_tasks + analysis_results`

### 第三步

- 统一 API schema 与前端类型
- 切换错误响应和状态枚举

### 第四步

- 再推进异步任务、监控、复盘闭环和更细测试

## 8. 最终结论

当前代码不是“完全不能用”，而是“已经能演示，但尚未进入可落地产品实现轨道”。

文档体系现在已经比代码实现更先进、更清晰，因此下一步不应该继续往旧实现上叠加功能，而应先完成：

- 身份边界收口
- 模型结构选型收口
- API 契约收口
- 安全配置收口

只有先把这四件事做完，后面的开发才不会持续返工。
