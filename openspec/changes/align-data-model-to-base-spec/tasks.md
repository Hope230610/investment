## 1. Contract

- [x] 1.1 冻结 `single-stock-analysis`、`pre-trade-check`、`post-trade-review` 的 delta spec，确认底层数据模型迁移后的接口语义不变
- [x] 1.2 冻结 `user-profile`、`history-and-review-loop` 的 delta spec，确认画像精简和外键变更范围
- [x] 1.3 创建 `data-model-analysis-v2`、`behavior-intervention-persistence`、`watchlist-normalization` 三个新 capability 的 delta spec
- [x] 1.4 映射 Phase 1~3 任务到 `structure/investment_team_execution_board.md` 的 TASK-BE-004 / TASK-BE-005 / TASK-BE-006 泳道
  - Phase 1（2.1-2.5）→ TASK-BE-011（数据库迁移 + 任务模型）
  - Phase 1 路由层（2.6-2.7）→ TASK-BE-007（API 路由切换）
  - Phase 2（2.8-2.10）→ TASK-BE-011 延续
  - Phase 3（2.11-2.17）→ TASK-BE-101（观察列表闭环）
  - 前端（3.1-3.6）→ TASK-FE-005（API 契约对齐）
  - QA（4.1-4.5）→ TASK-QA-004（迁移回归验证）
- [x] 1.5 确认 `action_type` 枚举字典命名规范，更新 `structure/db_types.ts` 补全 `UserActionType`

## 2. Backend/Data

### Phase 1: analysis 相关

- [x] 2.1 新建 `investment-back/src/models/analysis_task.py`（SQLAlchemy 模型，对应 `analysis_tasks` 表，字段含 `user_profile_snapshot`、`scenario_payload`、`started_at`、`completed_at`、`expired_at`）
- [x] 2.2 新建 `investment-back/src/models/analysis_result.py`（对应 `analysis_results` 表，含六段式决策卡、`detail_panels`、`valid_period`）
- [x] 2.3 新建 `investment-back/src/models/behavior_intervention.py`（对应 `behavior_interventions` 表，含冷静期、用户确认、动作归因）
- [x] 2.4 新建 Alembic 迁移 `002_add_analysis_v2_tables.py`：创建 `analysis_tasks`、`analysis_results`、`behavior_interventions` 三张新表
- [x] 2.5 编写数据迁移脚本：将现有 `analyses` 数据迁移到 `analysis_tasks`，`analysis_reasons` 按 `mark_type` 聚合到 `analysis_results.detail_panels`
- [x] 2.6 在 `AnalysisService` 中新增路由清单 `ANALYSIS_ROUTING`，初始值 `{"analysis": "old"}`，按 Phase 逐步切换
- [x] 2.7 后端接口同时接收 `int` 和 `uuid` 两种 `analysis_id`（迁移期兼容），路由参数类型改为 `str`，内部做类型推断判断走旧表还是新表

### Phase 2: 画像精简

- [x] 2.8 修改 `investment-back/src/models/user.py` 的 `UserProfile` 模型，精简字段集（移除 `investment_goals`、`portfolio_size`、`preferred_sectors`）
- [x] 2.9 新建 Alembic 迁移 `003_migrate_user_profiles.py`：快照备份后清理废弃字段，验证新字段约束
- [x] 2.10 补充 `behavior_interventions` 历史数据（从旧 `analyses.intervention` JSON 迁移到独立表）

### Phase 3: 观察 + 复盘 + 动作

- [x] 2.11 新建 `investment-back/src/models/watchlist.py`（合并后的 `watchlists` 表，移除 `focus_reasons` 分离）
- [x] 2.12 新建 `investment-back/src/models/user_action.py`（对应 `user_actions` 表）
- [x] 2.13 新建 Alembic 迁移 `004_migrate_watchlists.py`：合并 `watchlist_items` + `focus_reasons` 到 `watchlists`
- [x] 2.14 修改 `review_tasks` 外键：从 `ForeignKey("analyses.id")` 改为 `ForeignKey("analysis_tasks.id")`，新建迁移 `005_migrate_review_tasks_fk.py`
- [x] 2.15 新建 Alembic 迁移 `006_add_user_actions_table.py`：创建 `user_actions` 表

### 路由与验证

- [x] 2.16 修改 `investment-back/src/api/v1/analysis.py`：统一路由层根据 `ANALYSIS_ROUTING` 清单走新/旧 repository
- [x] 2.17 所有 Phase 执行完成后，将旧表 `analyses`、`analysis_reasons`、`watchlist_items`、`focus_reasons` 重命名为 `_*_legacy` 后缀（独立迁移文件）

## 3. Frontend

- [x] 3.1 更新 `investment-front/src/types.ts`：新增 `AnalysisTask`、`AnalysisResult`、`BehaviorInterventionRecord`、`WatchlistItemV2`、`UserAction` 类型，移除废弃字段类型
- [x] 3.2 新增 `AnalysisStatus` 枚举值 `partial_ready`，`id` 字段类型从 `number` 改为 `string`
- [x] 3.3 结果页 `ResultPage.tsx` 新增 `partial_ready` 状态 UI：复用结果页，加"部分就绪 / 数据不完整" banner，缺失模块做降级占位提示
- [x] 3.4 前端创建分析后按 string/UUID 跳转，不再对 id 做 `Number()` 转换（`SingleStockInput.tsx`、`PreTradeInput.tsx`、`PostTradeInput.tsx`）
- [x] 3.5 移除引用已废弃画像字段（`investment_goals`、`portfolio_size`、`preferred_sectors`）的组件代码
- [x] 3.6 运行 TypeScript 编译检查，确保无类型错误后提交

## 4. QA/Release

- [x] 4.1 Phase 1 迁移验证：执行 `alembic upgrade` 后运行主链路 smoke test（创建分析任务 → 查询结果 → 行为干预），确认新旧路由一致性
- [x] 4.2 Phase 2 迁移验证：画像更新接口字段校验通过，旧字段提交返回参数错误
- [x] 4.3 Phase 3 迁移验证：观察列表添加/删除、复盘任务创建/完成的端到端测试
- [x] 4.4 数据一致性验证：确认旧表 `*_legacy` 重命名后原接口仍能返回空结果（或友好提示），不报 500 错误
- [x] 4.5 回归测试：完整主链路（登录 → 分析 → 复盘 → 记录）端到端回归
- [x] 4.6 更新 `structure/investment_current_implementation_gap_audit.md`：标记数据模型 P0 差距已收口
