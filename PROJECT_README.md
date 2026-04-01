# AI 投资决策助手 - 项目总览

## 项目定位

AI 投资决策助手是一个面向 A 股普通投资者的 **AI 决策干预系统**，目标不是替用户选股或下交易指令，而是通过结构化分析、风险提示、用户适配、行为干预与复盘机制，帮助用户减少决策错误。

## 核心原则

- 不替用户做决策
- 不提供直接买卖指令
- 强调结构化判断、风险控制与用户适配
- 优先减少错误，而非追求收益最大化
- 行为干预优先于收益叙事
- 每个结论都必须绑定有效期、失效条件和复盘时间

## 三大核心场景

### 1. 单股咨询 `single_stock_check`

- 快速判断某只股票当前是否值得继续关注
- 帮助用户理解该标的与自己的匹配度
- 输出六段式决策卡片、关键原因和适配性判断

### 2. 交易前自检 `pre_trade_check`

- 在用户准备买入、加仓、减仓或卖出前识别情绪化触发
- 检查当前动作是否符合策略和风险边界
- 输出自检问题、等待条件与行为偏差提醒

### 3. 交易后复盘 `post_trade_review`

- 帮助用户区分判断质量、执行质量和运气因素
- 沉淀个人投资行为模式
- 输出归因分析与后续改进动作

## 核心能力

### 六段式决策卡

系统围绕统一的结果容器输出：

1. 一句话判断
2. 为什么
3. 适不适合我
4. 下一步
5. 主要风险
6. 复盘时间

### 用户适配机制

- 根据投资经验、持有周期、风险承受能力、行为标签调整表达强度和建议边界
- 明确“适合谁 / 不适合谁”
- 用户适配只影响解释方式和动作建议，不改写资产事实判断

### 行为干预机制

- 重点识别追涨、恐慌卖出、频繁换股等行为偏差
- 干预优先级高于常规分析结果
- 干预输出以冷静期、自检问题、等待条件、复盘建议为主

### AI 解释层

- 用通俗语言重述分析结论
- 将专业概念转成生活化表达
- 以“解释层”形式降低认知门槛，而不是生成新的交易结论

### 时间与复盘闭环

- 每个结论绑定有效期与复盘时间
- 超过有效期后自动降级为“需重新评估”
- 通过复盘任务帮助用户形成稳定方法论

### 输出标记

- `data_fact`: 可被数据直接支持的事实结论
- `model_inference`: 模型基于事实和规则形成的判断
- `uncertainty`: 样本不足、信号冲突或高不确定性部分

## 系统架构

```text
┌──────────────────────────────────────────────────────────────┐
│                        前端 (React Web)                      │
│  investment-front/                                           │
│  - React 19 + TypeScript + Vite                              │
│  - Tailwind CSS                                              │
│  - 移动端优先，兼容桌面端响应式                              │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              │ HTTP / REST API
                              │
┌─────────────────────────────┴────────────────────────────────┐
│                     后端 (Python / FastAPI)                  │
│  investment-back/                                            │
│  - FastAPI                                                   │
│  - SQLAlchemy 2.0                                            │
│  - Pydantic 2.x                                              │
│  - Structlog                                                 │
│  - Alembic                                                   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              │
┌─────────────────────────────┴────────────────────────────────┐
│                    数据层 (PostgreSQL 15+)                   │
│  结构设计参考：                                               │
│  - users / user_profiles                                     │
│  - stocks / watchlists                                       │
│  - analysis_tasks / analysis_results                         │
│  - behavior_interventions / review_tasks                     │
│  - user_actions / system_configs                             │
└──────────────────────────────────────────────────────────────┘
```

## 产品信息架构

### 页面结构

- 首页 `/`
- 用户画像页 `/profile`
- 股票搜索页 `/stock/search`
- 单股咨询输入页 `/analysis/single-stock`
- 交易前自检输入页 `/analysis/pre-trade`
- 交易后复盘输入页 `/analysis/post-trade`
- 分析结果页 `/analysis/:id/result`
- 复盘任务页 `/reviews`
- 历史记录页 `/records`

### 设计主线

- 首页负责入口选择、提醒汇总、最近使用和画像入口
- 输入页负责场景差异化采集
- 结果页统一承载行为干预、六段式决策卡、风险边界、AI 解释层和复盘动作
- 复盘页与记录页负责形成长期闭环

## 仓库结构

```text
F:/investment/
├── design/                                      # 产品方案文档
│   └── ai_investment_decision_system_v_4.md
├── structure/                                   # 架构与数据设计文档
│   ├── ai_investment_decision_system_ui_structure_design.md
│   ├── database_design.md
│   ├── db_types.ts
│   └── migrations/
├── investment-front/                            # React 前端
│   ├── src/
│   │   ├── pages/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── types.ts
│   │   └── utils.ts
│   ├── package.json
│   └── README.md
├── investment-back/                             # Python 后端
│   ├── src/
│   │   ├── api/                                 # API 路由与依赖
│   │   ├── core/                                # 配置与日志
│   │   ├── db/                                  # 数据库会话
│   │   ├── models/                              # SQLAlchemy 模型
│   │   ├── schemas/                             # Pydantic 模式
│   │   └── services/                            # 业务服务层
│   ├── alembic/
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
├── IMPLEMENTATION_PLAN.md
├── PROJECT_README.md
├── PROJECT_SUMMARY.md
├── start.bat
└── start.sh
```

## Python 后端说明

后端以 `investment-back/` 为主，采用 Python 技术栈：

- Web 框架：FastAPI
- ORM：SQLAlchemy 2.0
- 数据验证：Pydantic 2.x
- 数据库：PostgreSQL 15+
- 数据迁移：Alembic
- 日志：Structlog

### 后端分层

- `api/`: 路由、依赖注入、接口编排
- `schemas/`: 请求与响应数据结构
- `models/`: 数据库实体
- `services/`: 业务逻辑与规则处理
- `db/`: 会话与数据库连接管理
- `core/`: 配置、日志等核心基础设施

## 关键接口范围

当前后端围绕以下能力组织：

- 用户登录与用户画像管理
- 股票搜索与股票详情查询
- 分析任务创建与分析结果查询
- 观察列表管理
- 历史分析记录查询

## 开发方式

### 前端开发

```bash
cd investment-front
npm install
npm run dev
```

### Python 后端开发

```bash
cd investment-back
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- 前端：`http://localhost:5173`
- 后端 OpenAPI：`http://localhost:8000/api/v1/docs`

## 数据与迁移

数据库设计与迁移资料主要位于：

- `structure/database_design.md`
- `structure/migrations/001_init_schema.sql`
- `structure/migrations/002_init_data.sql`
- `structure/migrations/003_triggers.sql`

后端项目中同时提供 Alembic 基础配置，便于后续统一迁移流程。

## 适合阅读顺序

如果你要快速理解这个项目，建议按下面顺序阅读：

1. `design/ai_investment_decision_system_v_4.md`
2. `structure/ai_investment_decision_system_ui_structure_design.md`
3. `structure/database_design.md`
4. `investment-back/README.md`
5. `investment-front/README.md`

## 项目目标总结

这个项目的目标不是做一个“告诉用户买什么”的工具，而是构建一个围绕以下闭环运行的系统：

**结构化分析 → 用户适配 → 行为干预 → 时间复盘 → 方法论沉淀**

因此，前端负责承载用户输入、结果呈现与复盘体验，后端则以 **Python + FastAPI** 为核心，负责接口、业务规则、数据模型与后续 AI 分析能力的承接。
