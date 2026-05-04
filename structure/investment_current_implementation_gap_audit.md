# AI 投资决策助手 当前实现差距审查

更新时间：2026-04-08

## 1. 文档目的

本审查用于对照 `structure` 中已经形成的产品落地文档体系，判断当前真实代码实现还存在哪些关键差距。

审查范围：

- `investment-back`
- `investment-front`
- 当前 Alembic 与模型实现

审查标准：

- 以 `structure` 中已经冻结的产品、架构、认证、异常、安全、API、数据库基线为准

## 2. 总体结论

当前项目已经具备”可演示、可跑通部分主链路”的基础，已完成所有 P0 安全和可靠性缺口。

最突出的结论（2026-04-26 更新）：

1. ~~认证与身份边界尚未收口~~ ✅ 已收口（deps.py 无 debug fallback）
2. ~~后端数据模型仍是旧结构~~ ✅ 已收口（align-data-model-to-base-spec 变更）
3. ~~安全与配置底线未满足~~ ✅ 已收口（config.py _UNSAFE_DEFAULTS 检查）
4. ~~degrade_flags 链路未实现~~ ✅ 已收口（process_analysis_v2 异常写入 + 前端展示）
5. ~~异步任务架构~~ 🔄 基本拆分完成，队列语义已修正（RQ 队列 + workers 模块，2026-04-27）
6. API 契约收口（部分收口）

## 3. P0 Findings

### 3.1 开发态身份放行仍然存在

严重级别：P0

**状态：✅ 已收口（deps.py 已移除所有 debug fallback，无 token 直接抛 401）**

位置：

- [deps.py](F:/investment/investment-back/src/api/deps.py)

已修复：

- `get_current_user()` 已移除 DEBUG 条件分支，无 token 时直接抛出 401
- `_get_or_create_debug_user()` 已完全移除，不再在请求路径中隐式创建测试用户

### 3.2 启动时仍自动创建测试用户

严重级别：P0

**状态：✅ 已收口（main.py startup_event 已移除自动 seed 逻辑）**

位置：

- [main.py](F:/investment/investment-back/main.py)

已修复：

- `startup_event()` 已移除自动创建 `test@example.com` 的逻辑
- 运行时不再把生产与开发 seed 数据混写

### 3.3 默认安全配置不达标

严重级别：P0

**状态：✅ 已收口（config.py 增加了 _UNSAFE_DEFAULTS 检查，生产/非 DEBUG 环境强制拒绝不安全默认值）**

位置：

- [config.py](F:/investment/investment-back/src/core/config.py)

已修复：

- `DEBUG` 默认值改为 `False`
- 增加了 `_UNSAFE_DEFAULTS` 检查集（包含已知不安全默认值），生产/非 DEBUG 环境启动时硬失败
- `AI_API_KEY` 带默认值仅用于本地开发，但生产环境强制要求显式设置

### 3.4 后端核心数据模型仍是旧表结构

严重级别：P0

位置：

- [analysis.py](F:/investment/investment-back/src/models/analysis.py)
- [user.py](F:/investment/investment-back/src/models/user.py)
- [001_init_schema.py](F:/investment/investment-back/alembic/versions/001_init_schema.py)

问题：

- ~~当前后端仍使用旧表结构~~

**状态：✅ 已收口（align-data-model-to-base-spec 变更，2026-04-08）**

已完成：

- 新表 `analysis_tasks`、`analysis_results`、`behavior_interventions`、`watchlists`、`user_actions` 已创建
- 旧表 `analyses`、`analysis_reasons`、`watchlist_items`、`focus_reasons` 已重命名为 `*_legacy`
- 画像废弃字段（`investment_goals`、`portfolio_size`、`preferred_sectors`）已从模型和 Schema 移除
- 路由层支持双轨（`ANALYSIS_ROUTING = {"analysis": "old"}` 初始值），可渐进切换

遗留备注：

- 生产迁移需执行 `alembic upgrade head`，legacy 表数据已迁移到 `*_legacy` 表
- `review_tasks.analysis_id` 现为 nullable，双轨 FK 兼容新旧路径
- `users.email` 改为 nullable 以支持无 email 注册路径

## 4. P1 Findings

### 4.1 API 结构仍是旧版本，未对齐新 contract

严重级别：P1

位置：

- [analysis.py](F:/investment/investment-back/src/api/v1/analysis.py)
- [analysis.py](F:/investment/investment-back/src/schemas/analysis.py)
- [types.ts](F:/investment/investment-front/src/types.ts)

问题：

- ~~当前 API 和前端类型仍围绕旧的 `Analysis / AnalysisWithDetails / DecisionCard` 结构~~

**状态：🔄 部分收口（align-data-model-to-base-spec 变更）**

已完成：

- `schemas/analysis.py` 新增 `AnalysisRecord`、`DecisionCardV2`、`InterventionInfo`、`GetAnalysisResponseV2`、`ReviewTask`（含 dual `analysis_id`/`analysis_task_id`）
- `api/v1/analysis.py` 支持 UUID（new path）与 Integer（legacy path）双轨路由
- `types.ts` 新增 `AnalysisTask`、`AnalysisResult`、`BehaviorInterventionRecord`、`WatchlistItemV2`、`UserAction` 类型

遗留：

- `BehaviorIntervention.severity` 仍为宽泛字符串
- `MarketContext` 仍带 `tag` 字段
- 旧 `DecisionCard` 结构尚未完全迁移到 `DecisionCardV2`
- 错误响应 contract 尚未统一（`error.code`/`error.message`）

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

**状态：✅ 已收口（types.ts partial_ready + ResultPage.tsx UI + degrade_flags 链路全部完成）**

位置：

- [types.ts](F:/investment/investment-front/src/types.ts)
- [ResultPage.tsx](F:/investment-front/src/pages/ResultPage.tsx)

已完成：

- `types.ts` 中 `AnalysisStatus` 枚举已含 `partial_ready`
- `ResultPage.tsx` 中 `partial_ready` 状态 UI 已实现（banner + 降级占位）
- `degrade_flags` 字段已在 API 层填充（`process_analysis_v2` 异常写入 error_message；`_get_analysis_from_new_tables` 根据状态组装 flags）
- 前端 `partial_ready` banner 和 `failed` 状态均展示具体 degrade_flags 内容

### 4.4 后端仍采用同步背景任务模型，未真正走异步 worker 边界

严重级别：P1

**状态：🔄 基本拆分完成，队列语义已修正（2026-04-27）**

位置：

- [analysis.py](F:/investment-back/src/api/v1/analysis.py)
- [src/workers/](F:/investment-back/src/workers/)

已完成：

- `process_analysis_v2` 逻辑已提取到 `src/workers/tasks.py::run_analysis_job()`，作为唯一的任务执行函数
- `src/workers/dispatcher.py::enqueue_analysis_job()` 是 API 层唯一调用的投递接口：
  - `RQ_ASYNC=True`（默认，dev）：通过 FastAPI `BackgroundTasks` fire-and-forget 执行，API 请求立即返回
  - `RQ_ASYNC=False`（prod）：通过 RQ 将任务入 Redis 队列，由独立 worker 进程消费
- `create_analysis` 恢复 `BackgroundTasks` 依赖，通过 `enqueue_analysis_job(task_uuid, background_tasks)` 传递
- `src/workers/worker_main.py` 提供 `python -m src.workers` 入口，启动 RQ worker 监听 "analysis" 队列
- `requirements.txt` 新增 `rq==1.16.1` + `redis==5.0.8`
- `config.py` 新增 `REDIS_URL`（默认 `redis://localhost:6379/0`）和 `RQ_ASYNC` 配置项
- redis/rq 仅在 `_get_queue()`（生产路径）内部延迟导入，dev 路径完全不需要这些包参与模块加载
- `run_analysis_job()` 在持久化 FAILED 状态后重新抛出异常，确保 RQ 能正确标记任务失败（支持重试和告警）
- legacy `process_analysis` / `process_analysis_v2` 函数已删除（`ANALYSIS_ROUTING["analysis"] == "old"` 已废弃）

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

- ~~仍有不少旧结构字段，例如 `investment_goals`、`portfolio_size`、`preferred_sectors`~~

**状态：✅ 已收口（align-data-model-to-base-spec 变更，tasks 3.1、3.5）**

已完成：

- `types.ts` 已移除 `investment_goals`、`portfolio_size`、`preferred_sectors` 类型定义
- 前端页面已移除对废弃画像字段的引用

## 6. 当前实现与基线的匹配度判断

### 6.1 已经较接近的部分

- 前端页面骨架已存在
- 后端已有基本 API 分层
- 登录、分析、记录、复盘的概念链路已经有雏形
- 前后端都已具备进一步重构的基础

### 6.2 明显未对齐的部分

- ~~认证边界（debug 放行、自动测试用户）~~ ✅ 已收口
- ~~生产配置安全性（默认密钥）~~ ✅ 已收口
- ~~数据模型命名和结构~~ ✅ 已收口
- ~~`degrade_flags` 字段链路~~ ✅ 已收口
- ~~异步任务架构~~ 🔄 基本拆分完成，队列语义已修正（2026-04-27）
- API 契约（部分收口）
- 错误响应

## 7. 建议的修复顺序

### 第一步

- ~~关掉 debug 放行和启动自动测试用户~~ ✅ 已完成
- ~~修掉默认密钥与默认 AI key~~ ✅ 已完成

### 第二步

- 冻结真实后端目标数据模型
- 决定是否从旧 `analyses` 迁移到新 `analysis_tasks + analysis_results`

### 第三步

- 统一 API schema 与前端类型
- 切换错误响应和状态枚举

### 第四步

- 再推进异步任务、监控、复盘闭环和更细测试

## 8. 最终结论

当前代码不是”完全不能用”，而是”已经能演示，但尚未进入可落地产品实现轨道”。

2026-04-08 更新：align-data-model-to-base-spec 变更已收口 P0 数据模型差距，Phase 1~3 全部完成，Phase 4 QA/Release 全部通过。

2026-04-26 更新：P0 全部收口。
- 3.1 认证边界（debug fallback）：✅ 已移除
- 3.2 启动自动 seed：✅ 已移除
- 3.3 安全配置底线：✅ _UNSAFE_DEFAULTS 检查已上线
- 4.3 degrade_flags 链路：✅ 后端写入 + 前端展示全部完成

文档体系现在已经比代码实现更先进、更清晰，因此下一步不应该继续往旧实现上叠加功能，而应先完成：

- ~~模型结构选型收口~~ ✅ 已完成
- ~~身份边界收口（debug 放行）~~ ✅ 已完成
- ~~安全配置收口~~ ✅ 已完成
- ~~degrade_flags 链路收口~~ ✅ 已完成
- API 契约收口（错误响应、DecisionCardV2）
- 异步任务架构

只有先把这几件事做完，后面的开发才不会持续返工。
