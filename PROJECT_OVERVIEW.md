# AI 投资决策助手 — 产品概览

> 面向 A 股普通投资者的 AI 投资决策辅助产品，核心目标是通过结构化分析、风险提示、行为干预与复盘闭环，帮助用户减少决策错误，而不是直接给出买卖指令。

**技术栈**：React 19 + TypeScript + Vite（前端）/ FastAPI + SQLAlchemy + PostgreSQL（后端）
**最近一次 smoke 通过**：2026-04-22（commit 48c036f）

---

## 用户旅程

```
登录 → 首页（画像摘要 + 三大场景入口）
         │
         ├── 单股咨询（single_stock_check）
         ├── 交易前自检（pre_trade_check）
         ├── 交易后复盘（post_trade_review）  ← 核心，带 Learning Feedback
         │
         ├── 观察列表（watchlist）  ⚠️ 当前读 localStorage，暂未服务端化
         ├── 复盘任务（reviews）
         └── 画像配置（profile）
```

---

## 页面与路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/login` | 登录 | JWT 认证 |
| `/` | 首页 | 画像摘要、三大场景入口、观察列表、最近分析 |
| `/profile` | 画像页 | 投资经验/持有周期/风险承受能力/行为标签 + **学习记录趋势** |
| `/watchlist` | 观察列表 | ⚠️ 当前读 localStorage，无服务端同步 |
| `/stock/search` | 股票搜索 | A股搜索（名称/代码/拼音） |
| `/analysis/single-stock` | 单股咨询 | 选股票 → 提交 → 等结果 |
| `/analysis/pre-trade` | 交易前自检 | 意图/触发原因/情绪评估/高情绪触发问卷 → 结果 |
| `/analysis/post-trade` | 交易后复盘 | 操作记录/结果/偏离/判断质量/行为模式 → 结果 |
| `/analysis/:id/result` | 结果页 | 决策卡 + 核心理由 + 风险 + 行为干预 + Learning Feedback 卡 |
| `/reviews` | 复盘任务 | 待复盘/已完成列表 |
| `/records` | 历史记录 | 分析历史（新表路径：analysis_tasks） |
| `/me` | 个人中心 | 用户信息、退出 |

---

## 后端 API 概览

### 认证 `/api/v1/user`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/user/register` | 注册 |
| POST | `/user/login` | 登录，返回 JWT |
| GET | `/user` | 当前用户信息 |
| GET/PUT | `/user/profile` | 画像读写 |
| GET | `/user/profile/learning-history` | 学习历史（情绪+判断质量趋势） |
| POST | `/user/profile/learning-feedback` | 写入反馈（Step1：emotion_history + judgment_history + behavior_tags） |

### 分析 `/api/v1/analysis`

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/` | 创建分析（异步，返回 UUID） |
| GET | `/` | 分析记录列表（新表分支：analysis_tasks + analysis_results + stocks） |
| GET | `/{id}` | 分析详情（UUID 格式） |
| POST | `/{id}/record-reason` | 记录关注理由（幂等 upsert → watchlists v2） |

### 复盘 `/api/v1/reviews`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 复盘任务列表（含过期自动标记） |
| PATCH | `/{id}` | 更新复盘任务（整数 ID） |
| PATCH | `/by-analysis/{id}` | 通过 UUID 更新（Step2：review_tasks.status → completed） |

### 股票 `/api/v1/stocks`

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/search?q=&limit=` | 搜索 A股 |
| GET | `/{stock_id}` | 股票详情 |

### 观察列表 `/api/v1/watchlist`

> ⚠️ **废弃路径**。当前逻辑废弃，不再向前端新增调用。历史数据在 watchlist_items_legacy 表。

---

## 数据库模型

### 核心表

| 表 | 模型 | 说明 |
|---|---|---|
| `users` | `User` | 用户 |
| `user_profiles` | `UserProfile` | 画像（experience_level, risk_tolerance, behavior_tags…） |
| `stocks` | `Stock` | A股股票信息 |
| `analysis_tasks` | `AnalysisTask` | 新分析任务（UUID PK，Phase 2+） |
| `analysis_results` | `AnalysisResult` | 分析结果（六段式决策卡） |
| `review_tasks` | `ReviewTask` | 复盘任务 |
| `watchlists` | `Watchlist` | 观察列表（v2，UUID PK，UNIQUE user_id+stock_id） |
| `watchlist_items_legacy` | `WatchlistItem` | 旧观察列表（废弃） |
| `emotion_history` | `EmotionHistory` | 情绪历史（每日一条，UNIQUE user_id+recorded_date） |
| `judgment_history` | `JudgmentHistory` | 判断质量历史（UNIQUE user_id+judgment_date） |
| `behavior_interventions` | `BehaviorIntervention` | 行为干预记录 |

### 枚举

| 枚举 | 值 |
|---|---|
| `AnalysisScenarioEnum` | single_stock_check / pre_trade_check / post_trade_review |
| `AnalysisStatusEnum` | processing / partial_ready / ready / expired / failed |
| `ExperienceLevel` | novice / intermediate / expert |
| `RiskTolerance` | low / medium / high |
| `BehaviorTag` | chasing_rise / panic_sell / frequent_trading / stable_discipline |

---

## 核心功能流程

### 1. Learning Feedback 确认闭环（post_trade_review）

```
用户点"确认"
  → POST /api/v1/user/profile/learning-feedback
      写入 emotion_history + judgment_history（upsert，index_elements）
      ← 200
  → PATCH /api/v1/reviews/by-analysis/{id}
      review_tasks.status → completed（不是 upsert）
      ← 200（或 404 → 前端静默关闭，不报错）
  → localStorage.feedback_dismissed_${id} = 'true'
      读端归一化：'confirmed' → 'true'（修复 Gate 0 前遗留问题）
卡片关闭，刷新不再弹出
```

### 2. 分析创建（异步）

```
POST /api/v1/analysis → 创建 AnalysisTask（status=processing）→ 返回 UUID
后台任务：
  1. market_data_service 获取实时行情
  2. generation_service 生成 AI 分析（六段式决策卡）
  3. 更新 AnalysisTask + 创建 AnalysisResult（status=ready）
前端轮询 GET /api/v1/analysis/{id} 直到 status=ready
```

### 3. 记录页数据源（双轨现状）

```
GET /api/v1/records
  → ANALYSIS_ROUTING["analysis"] == "new" → 新表路径（analysis_tasks + analysis_results + stocks）
  → 否则 → 旧表路径（analyses legacy）

HomePage.tsx / RecordsPage.tsx 已切到 /api/v1/analysis（新表路径）
```

---

## 当前系统状态

### ✅ 已上线可用

- 登录/注册/JWT 认证
- 三大分析场景（单股咨询/交易前自检/交易后复盘）
- 异步分析生成（AI 六段式决策卡）
- 行为干预（情绪 >3 触发自检问卷）
- Learning Feedback 确认闭环（双写 + localStorage 归一化）
- 画像配置 + 学习记录趋势展示
- 关注理由记录（幂等 upsert）
- 复盘任务管理（自动过期标记）

### ⚠️ 已知技术债

| 问题 | 说明 | 优先级 |
|---|---|---|
| watchlist 读 localStorage | 前端观察列表非服务端同步，Profile 页无法展示"我的关注" | P1 |
| 旧表仍存在 | analyses / watchlist_items_legacy 未删除，仅路由废弃 | P2 |
| 无 E2E 测试 | 依赖人工 smoke | P1 |
| 无后端回归测试 | learning feedback 双写缺乏自动化守卫 | P1 |
| 错误响应不统一 | 后端用 `detail: str`，前端有 fallback 但用户体验不一致 | P2 |

### 🔒 安全配置现状

- DEBUG 默认 False ✅
- SECRET_KEY/AI_API_KEY 缺失时生产配置拒绝启动 ✅
- 无开发态自动创建测试用户 ✅
- JWT 鉴权严格，无 debug bypass ✅

---

## 目录结构

```
f:/investment/
├── investment-front/           # React 19 + TypeScript + Vite + Tailwind
│   └── src/
│       ├── api.ts             # 统一 API 请求封装（ApiError / parseErrorPayload）
│       ├── auth-context.tsx   # AuthProvider + RequireAuth
│       ├── auth.ts            # JWT 会话管理（localStorage）
│       ├── pages/             # 12 个页面组件
│       ├── components/        # LearningFeedbackCard、DecisionCard…
│       └── utils/             # learningFeedback.ts（含测试）
│
├── investment-back/            # FastAPI + SQLAlchemy + Alembic
│   └── src/
│       ├── api/v1/            # 路由层（analysis / reviews / user / stocks / watchlist）
│       ├── services/           # 业务逻辑（analysis_service / profile_service…）
│       ├── models/             # SQLAlchemy 模型
│       ├── schemas/            # Pydantic schemas
│       └── core/config.py     # 配置管理（生产安全校验）
│
├── openspec/                   # 规格治理
│   ├── specs/                 # Baseline specs（已同步 delta specs）
│   └── changes/               # Change proposals + archive
│
├── structure/                  # 长文基线文档（设计/架构/数据库）
├── alembic/versions/           # 数据库迁移（001-010）
└── SMOKE_RESULT_20260422.md    # 最新 smoke 验证结果
```

---

## 近期 commits

| Commit | 内容 |
|---|---|
| `48c036f` | smoke 验证通过 |
| `c102d6e` | record-reason upsert + 测试 + smoke checklist |
| `302e1fe` | delta specs 同步到主规格 |
| `dd7eba3` | Gate 0 baseline（ResultPage 归一化 + profile_service 修复 + records 新路径）|
| `e6b1db7` | 修复 GET /reviews 500 + 引入 vitest |
