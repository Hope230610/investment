# AI 投资决策助手前端

`investment-front` 是 AI 投资决策助手的前端项目。它不是传统的荐股或选股页面，而是围绕“结构化判断、行为干预、风险提示、复盘闭环”构建的决策辅助界面。

当前 README 主要依据以下设计文档整理，并结合现有前端实现做了落地说明：

- `../design/ai_investment_decision_system_v_4.md`
- `../structure/ai_investment_decision_system_ui_structure_design.md`
- `../structure/database_design.md`

## 1. 产品定位

项目服务于 A 股普通投资者，目标不是替用户下结论，而是帮助用户在关键时刻暂停、判断、约束、复盘，减少由情绪和认知偏差带来的错误决策。

核心原则：

- 不提供直接买卖指令
- 结论必须带适用前提、失效条件和复盘时间
- 行为干预优先级高于常规分析展示
- 用户画像只影响表达方式、风险边界和下一步建议，不改写资产事实判断

## 2. MVP 范围

设计文档定义的 MVP 聚焦三个核心场景：

- `single_stock_check`：单股咨询
- `pre_trade_check`：交易前自检
- `post_trade_review`：交易后复盘

围绕这三个场景，前端需要承接以下核心流程：

1. 用户进入首页并选择分析入口
2. 在场景输入页选择股票并填写最小必要信息
3. 发起分析任务，进入统一结果页
4. 查看六段式决策卡、行为干预、市场背景和解释层
5. 回到记录、复盘或观察列表，形成闭环

## 3. 当前实现总览

当前前端已经实现了设计中的主流程，并额外补充了登录鉴权与观察列表，便于真实联调和持续跟踪。

### 已实现页面

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/login` | 登录页 | 真实后端鉴权入口，补充于原 UI 设计之外 |
| `/` | 首页 | 场景入口、画像摘要、观察列表、待复盘提醒、最近分析 |
| `/profile` | 用户画像页 | 编辑经验、持有周期、风险承受、行为标签 |
| `/watchlist` | 观察列表页 | 对设计中“加入观察列表/保存动作”的独立承接页 |
| `/stock/search` | 股票搜索页 | 实时搜索 A 股标的，支持回填场景页和加入观察列表 |
| `/analysis/single-stock` | 单股咨询输入页 | 发起 `single_stock_check` |
| `/analysis/pre-trade` | 交易前自检输入页 | 发起 `pre_trade_check`，含情绪分级与自检问题 |
| `/analysis/post-trade` | 交易后复盘输入页 | 发起 `post_trade_review`，记录执行与归因信息 |
| `/analysis/:id/result` | 统一结果页 | 轮询分析结果，展示决策卡、干预卡、市场背景、解释层等 |
| `/reviews` | 复盘任务页 | 查看待复盘和已完成复盘 |
| `/records` | 历史记录页 | 查看历史分析记录并按场景筛选 |

### 当前结果页已承接的核心模块

- 风险声明
- 行为干预卡
- 六段式决策主卡
- 用户适配信息
- 下一步行动建议
- 风险与有效期提示
- 市场背景卡
- 公司概况
- 最近公告与事件
- AI 解释抽屉
- 加入观察列表 / 记录关注理由

## 4. 设计与实现的对应关系

### 已较好对齐的部分

- 首页采用场景驱动，突出三大分析入口
- 使用统一结果页承接三类分析任务
- 保留“行为干预优先”的产品机制
- 用户画像单独成页，并影响后续分析表达
- 支持复盘任务与历史记录闭环

### 当前实现中的补充

- 增加了登录态与路由守卫，便于接真实后端
- 增加了独立的观察列表页 `watchlist`
- 使用本地存储承接观察列表和部分关注理由

### 仍待继续补齐的设计点

- 更完整的桌面端三栏布局
- 设计稿中的 `partial_ready` 等更细粒度结果状态
- 输入页草稿缓存、最近搜索与更多异常态
- AI 解释层的“更简单 / 更专业”双档切换
- 更完整的数据来源、详细推理和失效条件分层展示
- 部分源码中文文案仍需统一为 UTF-8 编码

## 5. 技术栈

- React 19
- TypeScript
- React Router 7
- Vite 6
- Tailwind CSS 4
- Motion
- Express 作为本地开发服务器与 API 代理

## 6. 前端架构

### 运行方式

本项目不是直接使用 `vite dev server` 对外提供服务，而是通过 `server.ts` 启动一个 Express 服务：

- 开发环境下挂载 Vite middleware
- 将 `/api/*` 请求代理到后端服务
- 前端统一使用相对路径 `/api/v1/*` 调用后端

默认代理目标：

- `http://localhost:8000`

可通过环境变量覆盖：

- `BACKEND_BASE_URL`

### 关键模块

- `src/pages/`：页面级组件
- `src/api.ts`：统一请求封装，处理鉴权和错误
- `src/auth.ts`：登录态本地存储
- `src/auth-context.tsx`：认证上下文和路由守卫
- `src/types.ts`：前后端交互类型
- `src/utils.ts`：场景配置、观察列表与关注理由的本地工具

## 7. 目录结构

```text
investment-front/
├─ src/
│  ├─ pages/
│  ├─ api.ts
│  ├─ auth.ts
│  ├─ auth-context.tsx
│  ├─ types.ts
│  ├─ utils.ts
│  ├─ App.tsx
│  └─ main.tsx
├─ server.ts
├─ vite.config.ts
├─ package.json
└─ README.md
```

## 8. 本地开发

### 环境要求

- Node.js 18+
- npm
- 可用的后端服务，默认地址为 `http://localhost:8000`

### 安装依赖

```bash
npm install
```

### 启动开发环境

如果后端就是默认地址，直接运行：

```bash
npm run dev
```

如果需要指定后端地址：

```powershell
$env:BACKEND_BASE_URL="http://localhost:8000"
npm run dev
```

启动后访问：

- `http://localhost:3000`

### 其他命令

```bash
npm run build
npm run preview
npm run lint
```

说明：

- `npm run build`：构建前端静态资源
- `npm run preview`：预览 Vite 构建产物
- `npm run lint`：当前实际执行 TypeScript 类型检查

## 9. 接口依赖

当前前端默认依赖以下后端接口：

### 用户与鉴权

- `POST /api/v1/user/login`
- `GET /api/v1/user`
- `GET /api/v1/user/profile`
- `PUT /api/v1/user/profile`

### 股票

- `GET /api/v1/stocks/search?q=关键词&limit=12`

### 分析

- `POST /api/v1/analysis`
- `GET /api/v1/analysis/:id`
- `POST /api/v1/analysis/:id/record-reason`

### 记录与复盘

- `GET /api/v1/reviews`
- `GET /api/v1/records`

其中 `POST /api/v1/analysis` 由三种场景共用，请求体核心结构如下：

```json
{
  "scenario": "single_stock_check | pre_trade_check | post_trade_review",
  "stock_id": "股票代码",
  "scenario_payload": {}
}
```

## 10. 本地存储

前端当前使用 `localStorage` 保存部分状态：

- `ai_investment_access_token`：访问令牌
- `ai_investment_user`：当前用户信息
- `ai_investment_watchlist`：观察列表
- `ai_investment_focus_reasons`：关注理由

注意：

- 观察列表当前以前端本地存储为主，不依赖后端持久化
- 关注理由在结果页会同时尝试调用后端接口并写入本地缓存

## 11. 与数据库设计的关系

`../structure/database_design.md` 定义了用户、画像、股票、分析任务、分析结果、行为干预、复盘任务等核心数据模型。前端当前的 `src/types.ts` 已经围绕这些实体建立了主要的请求响应类型，后续联调时应优先以数据库设计和后端接口契约为准。

## 12. 推荐协作方式

如果后续继续推进该项目，建议按下面顺序协作：

1. 先以 `design` 和 `structure` 文档为产品基线
2. 以前端 README 和 `src/types.ts` 作为联调入口
3. 后端返回结构优先向统一结果页靠拢，而不是按页面分散定制
4. 每次新增能力时，同时更新 README、接口类型和页面映射

## 13. 一句话总结

这个前端项目的核心不是“展示股票信息”，而是把设计稿中的场景驱动、行为干预、统一结果页和复盘闭环真正落到可联调、可迭代的 React 应用里。
