## Why

当前代码中的数据库模型仍是旧结构（`analyses`、`analysis_reasons`、`watchlist_items`、`focus_reasons`），与 `structure/database_design.md` 中已冻结的目标基线存在系统性分叉。代码与文档各成一套，导致新功能无法基于目标基线开发，历史数据与新功能混在一起，API 层也无法稳定演进。必须用增量迁移的方式将数据库结构对齐目标基线，并确保 API 层通过统一路由逐步切换，不产生破坏性变更。

## What Changes

- 新增目标基线定义的全部核心表（`analysis_tasks`、`analysis_results`、`behavior_interventions`、`watchlists`、`user_actions`、`system_configs`）
- 按依赖顺序分三阶段将旧表数据迁移到新表，建新表时立即迁移历史数据
- API 层改为统一路由模式，内部根据目标 schema 版本判断走新表还是旧表，逐步将路由权重从旧表切向新表
- 旧表在所有功能稳定迁移完成后归档废弃，不在使用期间删除
- 用户画像精简到基线定义的最小集（移除 `investment_goals`、`portfolio_size`、`preferred_sectors` 等旧字段）
- 所有表主键从 Integer 迁移到 UUID，符合基线设计

## Capabilities

### New Capabilities

- `data-model-analysis-v2`: 分析任务与结果分离为 `analysis_tasks`（任务生命周期）+ `analysis_results`（六段式决策卡），支持 `partial_ready` 中间状态，满足单股咨询/交易前检查/交易后复盘三个场景的结构化输入输出
- `behavior-intervention-persistence`: 行为干预独立存储，支持冷静期追踪、用户确认反馈和动作归因，解决当前干预数据以 JSON 内嵌导致的查询和审计困难
- `watchlist-normalization`: 观察列表从 `watchlist_items + focus_reasons` 两表合并为单一 `watchlists` 表，消除冗余关系，降低维护成本

### Modified Capabilities

- `single-stock-analysis`: 底层数据模型从 `analyses` 迁移到 `analysis_tasks + analysis_results`，API 内部路由切换，不影响对外接口语义；新增 `partial_ready` 状态满足规格中的部分可读场景
- `pre-trade-check`: 同 `single-stock-analysis`，共享新的分析任务/结果数据模型
- `post-trade-review`: 底层从旧 `analyses` + `analysis_reasons` 迁移到新 `analysis_tasks + analysis_results`，归因结构对齐基线 JSON schema
- `user-profile`: 画像字段集从旧字段（`investment_goals`、`portfolio_size`、`preferred_sectors`）精简到基线定义集（`experience_level`、`holding_horizon`、`risk_tolerance`、`behavior_tags`、`profile_source`），历史数据同步清理
- `history-and-review-loop`: 复盘任务表 `review_tasks` 改关联 `analysis_tasks` 而非旧 `analyses`，外键约束加强

## Impact

- 关联 `structure` 基线文档：`database_design.md`、`investment_current_implementation_gap_audit.md`、`investment_api_contract_and_implementation_alignment.md`
- 受影响泳道：后端 `TASK-BE-004`（数据模型迁移）、`TASK-BE-005`（API 路由切换）、`TASK-BE-006`（存量数据迁移）；前端 `TASK-FE-006`（类型对齐新 schema）；测试 `TASK-QA-004`（迁移回归验证）
- 受影响代码区域：
  - `investment-back/src/models/`（新建 `analysis_task.py`、`analysis_result.py`、`behavior_intervention.py`、`watchlist.py`、`user_action.py`；修改 `user.py` 主键类型）
  - `investment-back/src/schemas/`（对齐新 JSON 结构）
  - `investment-back/src/api/v1/analysis.py`（统一路由切换逻辑）
  - `investment-back/alembic/versions/`（新增迁移文件）
  - `investment-front/src/types.ts`（对齐新枚举和类型）
  - `investment-front/src/api.ts`（错误和返回类型对齐）
