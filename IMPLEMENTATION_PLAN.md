# AI 投资决策系统 - 实施计划

基于产品设计文档 `design/ai_investment_decision_system_v_4.md` 的核心思路制定。

---

## 一、项目现状分析

### 1.1 已完成部分

#### 前端 (investment-front)
- ✅ 整体UI框架搭建完成
- ✅ 三个核心入口页面：单股咨询、交易前自检、交易后复盘
- ✅ 六段式决策卡片UI结构
- ✅ 用户画像页面
- ✅ 行为干预界面
- ✅ AI解释层（通俗解释功能）
- ✅ 复盘提醒和历史记录页面

#### 数据库设计
- ✅ 基础表结构设计
- ✅ SQL迁移脚本（001_init_schema.sql, 002_init_data.sql, 003_triggers.sql）

### 1.2 前端UI与产品设计的匹配度分析

| 产品设计要求 | 前端实现状态 | 说明 |
|------------|------------|------|
| 三个核心入口 | ✅ 已实现 | single_stock_check, pre_trade_check, post_trade_review |
| 六段式决策卡片 | ✅ 已实现 | 一句话判断、为什么、适不适合我、下一步、主要风险、复盘时间 |
| 用户画像 | ✅ 已实现 | 经验水平、持有周期、风险承受、行为标签 |
| 行为干预 | ✅ 已实现 | 追涨、恐慌卖出等场景识别 |
| AI问投资 | ✅ 已实现 | 通俗解释、生活化类比 |
| 加入观察列表 | ❌ 未实现 | 只有UI按钮，无功能 |
| 记录关注理由 | ❌ 未实现 | 只有UI按钮，无功能 |
| 时间维度机制 | ⚠️ 部分实现 | 有复盘时间，但缺少过期自动降级 |
| 输出标记 | ❌ 未实现 | data_fact / model_inference / uncertainty |

---

## 二、技术选型决策

### 2.1 后端语言选型

基于用户之前询问"为什么不用Python作为后端语言"，现重新评估：

| 对比项 | Node.js/TypeScript | Python | 推荐 |
|-------|-------------------|--------|------|
| 前端技术栈一致性 | ✅ 高 - 统一TypeScript | ⚠️ 中 - 需维护两种语言 | Node.js |
| AI/ML生态 | ⚠️ 需额外配置 | ✅ 丰富 - PyTorch, TensorFlow, LangChain | Python |
| 数据处理能力 | ✅ 良好 | ✅ 优秀 - Pandas, NumPy | Python |
| 异步性能 | ✅ 优秀 | ⚠️ 需使用asyncio | Node.js |
| 团队熟悉度 | ⚠️ 未知 | ⚠️ 未知 | - |

**最终决策：采用 Python + FastAPI 作为后端**
- 理由：产品核心是AI投资决策，Python在AI/ML和数据处理方面有明显优势
- 同时保持前端TypeScript不变

---

## 三、实施计划

### 阶段一：前端功能完善（优先级：高）

#### 任务 1.1：实现观察列表功能
- [ ] 创建 `WatchlistPage.tsx` 页面
- [ ] 在ResultPage添加"加入观察列表"按钮功能
- [ ] 在HomePage显示观察列表摘要
- [ ] 添加/移除观察列表项的交互

#### 任务 1.2：实现关注理由记录功能
- [ ] 在ResultPage添加关注理由输入弹窗
- [ ] 创建关注理由记录存储（localStorage临时方案）
- [ ] 在复盘时显示当初的关注理由

#### 任务 1.3：完善输出标记功能
- [ ] 在ResultPage中添加 `data_fact` / `model_inference` / `uncertainty` 标记
- [ ] 设计标记的视觉呈现方式
- [ ] 实现标记的交互说明

#### 任务 1.4：完善时间维度机制
- [ ] 添加结论过期状态显示
- [ ] 实现过期后"需重新评估"提示
- [ ] 添加复盘提醒通知

### 阶段二：Python后端开发（优先级：高）

#### 任务 2.1：项目初始化
- [ ] 创建 `investment-back-py/` 目录结构
- [ ] 配置 FastAPI + Uvicorn
- [ ] 配置 Pydantic 数据验证
- [ ] 配置 SQLAlchemy ORM
- [ ] 配置 logging 日志系统
- [ ] 创建 requirements.txt

#### 任务 2.2：数据库连接与模型
- [ ] 实现 PostgreSQL 连接池
- [ ] 创建 SQLAlchemy 模型（对应现有表结构）
- [ ] 实现数据库迁移脚本集成

#### 任务 2.3：核心API接口实现
- [ ] `GET /api/v1/health` - 健康检查
- [ ] `GET /api/v1/user/profile` - 获取用户画像
- [ ] `PUT /api/v1/user/profile` - 更新用户画像
- [ ] `GET /api/v1/stocks/search` - 搜索股票
- [ ] `POST /api/v1/analysis` - 创建分析任务
- [ ] `GET /api/v1/analysis/:id` - 获取分析结果
- [ ] `GET /api/v1/reviews` - 获取待复盘任务
- [ ] `GET /api/v1/records` - 获取分析记录
- [ ] `POST /api/v1/reviews/:id` - 提交复盘
- [ ] `GET /api/v1/watchlist` - 获取观察列表
- [ ] `POST /api/v1/watchlist` - 添加观察列表项
- [ ] `DELETE /api/v1/watchlist/:id` - 移除观察列表项

#### 任务 2.4：业务逻辑层实现
- [ ] UserService - 用户画像管理
- [ ] StockService - 股票数据服务
- [ ] AnalysisService - 分析任务管理
- [ ] ReviewService - 复盘管理
- [ ] WatchlistService - 观察列表管理

### 阶段三：核心业务逻辑实现（优先级：最高）

#### 任务 3.1：用户适配机制
- [ ] 实现基于用户画像的适配逻辑
- [ ] 经验水平决定解释深度
- [ ] 持有周期决定时间维度
- [ ] 风险承受决定风险阈值
- [ ] 行为标签决定干预优先级

#### 任务 3.2：行为干预机制
- [ ] 实现追涨场景识别
- [ ] 实现恐慌卖出场景识别
- [ ] 实现频繁换股场景识别
- [ ] 生成干预问题列表
- [ ] 实现冷静期逻辑

#### 任务 3.3：六段式决策卡片生成（模拟）
- [ ] 实现一句话判断生成
- [ ] 实现核心原因总结
- [ ] 实现用户适配判断
- [ ] 实现下一步建议
- [ ] 实现风险提示
- [ ] 实现复盘时间计算

#### 任务 3.4：AI解释层
- [ ] 实现通俗解释生成
- [ ] 实现生活化类比
- [ ] 实现常见误解提醒

### 阶段四：数据库完善（优先级：中）

#### 任务 4.1：确认并完善表结构
- [ ] 确认 users, user_profiles 表结构
- [ ] 确认 stocks, watchlists 表结构
- [ ] 确认 analysis_tasks, analysis_results 表结构
- [ ] 确认 behavior_interventions, review_tasks 表结构
- [ ] 确认 user_actions, system_configs 表结构
- [ ] 添加关注理由字段到相关表

#### 任务 4.2：添加索引和优化
- [ ] 为常用查询添加索引
- [ ] 优化视图查询性能
- [ ] 添加必要的约束

### 阶段五：集成与测试（优先级：高）

#### 任务 5.1：前后端集成
- [ ] 配置前端API_BASE_URL
- [ ] 实现前端API调用封装
- [ ] 实现错误处理和loading状态
- [ ] 实现用户session管理

#### 任务 5.2：MVP测试
- [ ] 测试三个核心入口流程
- [ ] 测试用户画像适配
- [ ] 测试行为干预触发
- [ ] 测试复盘流程
- [ ] 测试观察列表功能

#### 任务 5.3：验证产品设计场景
- [ ] 验证：同一股票面对不同用户画像输出不同
- [ ] 验证：高风险场景优先给出限制条件
- [ ] 验证：行为干预优先于股票分析
- [ ] 验证：未知用户自动切换保守策略
- [ ] 验证：过期结论提示重新评估

### 阶段六：部署准备（优先级：中）

#### 任务 6.1：本地开发环境优化
- [ ] 创建一键启动脚本（支持Windows/macOS/Linux）
- [ ] 配置Docker Compose（可选）
- [ ] 编写开发环境文档

#### 任务 6.2：生产部署准备
- [ ] 配置环境变量管理
- [ ] 配置日志收集
- [ ] 配置健康检查
- [ ] 编写部署文档

---

## 四、技术栈详情

### 前端技术栈
- React 19 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Lucide React (图标)
- Motion (动画)

### 后端技术栈（Python）
- FastAPI (Web框架)
- Uvicorn (ASGI服务器)
- SQLAlchemy (ORM)
- Pydantic (数据验证)
- PostgreSQL (数据库)
- Psycopg2 (PostgreSQL驱动)
- Python-Multipart (表单数据处理)
- Python-Jose (JWT，可选)

---

## 五、目录结构规划

```
F:\investment\
├── investment-front/          # 现有前端项目
├── investment-back-py/        # 新Python后端项目
│   ├── src/
│   │   ├── api/               # API路由
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── stock.py
│   │   │   ├── analysis.py
│   │   │   ├── review.py
│   │   │   └── watchlist.py
│   │   ├── core/              # 核心业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── user_adapter.py
│   │   │   ├── behavior_intervention.py
│   │   │   ├── decision_card.py
│   │   │   └── ai_explanation.py
│   │   ├── models/            # 数据模型
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   └── schemas.py
│   │   ├── services/          # 服务层
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── stock_service.py
│   │   │   ├── analysis_service.py
│   │   │   ├── review_service.py
│   │   │   └── watchlist_service.py
│   │   ├── config.py          # 配置
│   │   └── main.py            # 入口
│   ├── tests/
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
└── ...
```

---

## 六、实施时间表

| 阶段 | 任务 | 预估时间 | 依赖 |
|-----|------|---------|------|
| 第一周 | 阶段一：前端功能完善 | 3-5天 | - |
| 第二周 | 阶段二：Python后端开发 | 5-7天 | - |
| 第三周 | 阶段三：核心业务逻辑 | 5-7天 | 阶段二 |
| 第四周 | 阶段四、五：数据库、集成测试 | 5-7天 | 阶段一、二、三 |
| 第五周 | 阶段六：部署准备 | 2-3天 | 阶段四、五 |

**总计：约4-5周完成MVP**

---

## 七、风险与应对

| 风险 | 影响 | 概率 | 应对措施 |
|-----|------|------|---------|
| Python后端开发周期长 | 高 | 中 | 先实现核心API，简化非必要功能 |
| AI决策逻辑复杂度高 | 高 | 高 | MVP阶段使用模拟数据，后续迭代完善 |
| 前后端集成问题 | 中 | 中 | 提前定义API接口文档，使用Mock数据 |
| 数据库性能问题 | 中 | 低 | 先实现功能，后期优化索引和查询 |

---

## 八、成功标准

### MVP验证指标
1. ✅ 三个核心入口完整流程跑通
2. ✅ 用户画像能影响输出结果
3. ✅ 行为干预能正确触发
4. ✅ 复盘闭环完整
5. ✅ 前端UI符合产品设计六段式卡片
6. ✅ 观察列表和关注理由功能可用

### 产品测试场景验证
1. 同一股票不同用户画像输出不同 ✓
2. 高风险场景优先限制条件 ✓
3. 行为干预优先于股票分析 ✓
4. 未知用户自动保守策略 ✓
5. 过期结论提示重新评估 ✓
