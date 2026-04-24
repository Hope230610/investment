## Context

当前 `investment-back/src/models/analysis.py` 中的数据库模型是 MVP 阶段的旧结构，`analyses` 表混合了"任务生命周期"与"结果数据"，所有分析理由以松散外键关联，行为干预以内嵌 JSON 为主，观察列表拆成了 `watchlist_items` 和 `focus_reasons` 两张表。这与 `structure/database_design.md` 中已冻结的目标基线存在系统性差距：

| 维度 | 当前（旧） | 目标（新） |
|------|-----------|-----------|
| 主键 | Integer | UUID |
| 分析表 | `analyses`（混合 task + result） | `analysis_tasks` + `analysis_results` |
| 干预 | 内嵌 JSON | 独立 `behavior_interventions` 表 |
| 观察列表 | `watchlist_items` + `focus_reasons` | 单一 `watchlists` |
| 复盘 | 关联旧 `analyses` | 关联 `analysis_tasks` |
| 画像 | 含 `investment_goals` 等旧字段 | 仅基线定义字段 |
| 状态枚举 | 缺 `partial_ready` | 含 `partial_ready` |

目标基线已将分析流程拆为"任务创建"（analysis_tasks）与"结果输出"（analysis_results）两部分，并在 `database_design.md` 中定义了完整的 JSON 结构规范（`user_profile_snapshot`、`scenario_payload`、`user_fit_summary`、`intervention`、`market_context` 等）。

## Goals / Non-Goals

**Goals:**
- 用增量迁移方式将数据库模型对齐目标基线，建新表时立即迁移历史数据
- API 层改为统一路由模式，内部按 schema 版本路由，外部接口语义不变
- 用户画像精简到基线定义的最小集，历史数据同步清理
- 所有表主键迁移到 UUID
- 迁移期间新功能在旧表上继续可用，不阻塞产品迭代

**Non-Goals:**
- 不在迁移期间删除旧表，待全部稳定后归档废弃
- 不改变 API 外部接口的请求/响应结构（对前端透明）
- 不做用户数据的大规模清洗或重写（仅移除明确废弃的字段）
- 不做性能优化或索引重建（留待后续专项 change）

## Decisions

### 决策 1：分三阶段按依赖顺序迁移

选择按功能优先级分三阶段，不按表依赖关系：

- **Phase 1（analysis 相关）**：`analyses` → `analysis_tasks` + `analysis_results`；新建 `behavior_interventions`；迁移 `analysis_reasons` 到新 `analysis_results.detail_panels`
- **Phase 2（画像 + 干预）**：`user_profiles` 精简字段 + 迁移到 UUID；`behavior_interventions` 补充历史干预数据
- **Phase 3（观察 + 复盘 + 动作）**：`watchlist_items` + `focus_reasons` → `watchlists`；`review_tasks` 外键从 `analyses.id` 改为 `analysis_tasks.id`；新增 `user_actions` 表

理由：分析流程是产品核心业务，先完成核心迁移可以让新功能的开发基础稳固，再向外围扩展。存量数据迁移在每阶段建新表时同步执行，避免后期批量迁移的集中风险。

放弃的替代方案：按表依赖顺序（先 `user_profiles` 再 `stocks` 再 `analysis_tasks`），因为 `user_profiles` 依赖简单，独立迁移价值低，按功能优先级更符合迭代节奏。

### 决策 2：API 统一路由，版本协商切换

选择方案：同一 API 路由内部判断走新表还是旧表，不新建 `/api/v2/` 路径。

路由层维护一张"表切换清单"（例如 `ANALYSIS_ROUTING = {"analysis": "new"}`），每个受影响的 repository/service 方法先查清单再选表。当 `ANALYSIS_ROUTING["analysis"] == "new"` 时走新表，否则走旧表。

理由：前端不需要感知后端迁移进度，保持单一 API 版本降低联调复杂度；内部路由清单可以在每个 Phase 完成后独立修改，实现渐进式切换。后期稳定后统一切到新表，路由清单废弃。

放弃的替代方案 A：新建 `/api/v2/`，优点是彻底隔离但需要前端配合适配，会阻断正常迭代。替代方案 B：不做内部路由，所有请求同时读写新旧表（双写），实现复杂且一致性风险高。

### 决策 3：画像精简不迁移历史数据

选择方案：`user_profiles` 表移除 `investment_goals`、`portfolio_size`、`preferred_sectors` 等旧字段，旧数据直接清理，不做字段映射迁移。

理由：这些字段在基线设计中已被明确废弃，不属于用户核心画像的一部分，保留它们只会让前端类型和接口定义持续混乱。历史数据本身价值有限（内测阶段），清理成本远低于维持兼容的成本。

放弃的替代方案：保留旧字段并映射到新结构（BETWEEN 映射表），增加维护负担但收益极低。

### 决策 4：主键迁移使用 UUID，无需外键级联更新

选择方案：新表使用 SQLAlchemy `Uuid` 类型（底层 `UUID`），旧表保留 `Integer` 主键，通过 `stock_code` / `user_id` 等业务键做数据迁移映射，不做外键级联 UUID 重写。

理由：`analyses` 与其他表的外键关系复杂（`review_tasks`、`analysis_reasons`），若所有表同步改 UUID 主键，外键更新范围过大。增量迁移期间新旧表并存，旧表主键不变，新表用 UUID，跨表查询通过业务键或临时映射表桥接，稳定后再统一规划外键。

放弃的替代方案：一次性把所有表主键从 Integer 改为 UUID，外键同步更新，工作量巨大且风险高。

### 决策 5：存量数据迁移使用 Alembic 迁移脚本

选择方案：每个 Phase 新建一个 Alembic 迁移文件（如 `002_migrate_to_analysis_v2.py`），包含数据迁移 SQL + 新表 DDL，统一通过 `alembic upgrade head` 执行。

理由：Alembic 迁移天然支持版本化、可回滚，与现有 `001_init_schema.py` 一脉相承。每个 Phase 独立迁移文件降低单次变更风险，失败时只回滚当前 Phase。

## Risks / Trade-offs

- **[数据一致性风险]** 迁移期间新表和旧表同时存在，若 API 路由切换不完整会导致数据写错表 → 缓解：每个 Phase 有独立的迁移验证测试，写操作优先切新表，读操作双读校验
- **[历史数据丢失风险]** 画像旧字段清理无法回滚 → 缓解：Phase 2 迁移前做数据快照备份，确认无重要数据后再清理
- **[前端类型断裂风险]** 前端 `types.ts` 对齐新 schema 期间，旧页面可能引用已移除的字段 → 缓解：前端按模块逐步对齐，每次提交前跑类型检查
- **[迁移时间窗口]** 每次 `alembic upgrade` 需要停机或锁表 → 缓解：使用 `pg` 在线 DDL 操作，大表迁移在低峰期执行
- **[双重维护成本]** API 层需要同时支持新旧表路由直到旧表废弃 → 缓解：每个 Phase 完成后记录路由切换进度，设置明确的旧表废弃时间节点

## Migration Plan

### Phase 1：analysis 相关迁移

1. 新建 `analysis_tasks` + `analysis_results` 表模型（SQLAlchemy）
2. 编写 Alembic 迁移 `002_add_analysis_v2_tables.py`：创建新表结构 + 迁移 `analyses` 数据到 `analysis_tasks`，生成 `analysis_results`
3. 新建 `behavior_interventions` 表模型
4. 修改 `AnalysisService` 增加路由清单，按清单选择新/旧表
5. 写单元测试：创建/读取/更新走新表路径
6. 前端类型对齐（`types.ts` 新增 `AnalysisTask`、`AnalysisResult` 类型）
7. QA 验证：主链路 smoke test

### Phase 2：画像精简 + UUID 迁移

1. 修改 `UserProfile` 模型，精简字段集
2. Alembic 迁移 `003_migrate_user_profiles.py`：改主键为 UUID + 清理旧字段
3. 快照备份 `user_profiles` 数据后执行清理
4. 前端类型清理（移除旧画像字段引用）

### Phase 3：观察 + 复盘 + 动作表

1. 新建 `Watchlist`（单表）+ `UserAction` 模型
2. Alembic 迁移 `004_migrate_watchlists.py`：合并 `watchlist_items` + `focus_reasons`
3. 修改 `ReviewTask` 外键从 `analyses.id` 改为 `analysis_tasks.id`
4. 新增 Alembic 迁移 `005_add_user_actions.py`
5. 全量集成验证

### 稳定后：旧表归档

- 所有 Phase 验证通过后，将 `analyses`、`analysis_reasons`、`watchlist_items`、`focus_reasons` 重命名为 `_*_legacy` 后缀
- 确认无误后删除旧表（独立迁移文件，不在日常发布中执行）

## Open Questions

~~1. **Phase 2 快照备份方案**：PostgreSQL 逻辑备份（`pg_dump --data-only`）还是应用层导出 JSON？~~ → **已确认：pg_dump --data-only**
  - 使用 `pg_dump --data-only --table=user_profiles` 做正式快照
  - 备份文件放部署环境受控备份目录或对象存储，**不放入仓库、不放入 f:\investment 工作区**
  - JSON 仅作为人工核对辅助，不作为主备份

~~2. **UUID 主键下的 API 兼容**：前端 URL 变化（如 `/analysis/1` → `/analysis/uuid-xxx`）是否需要 ID 映射路由？~~ → **已确认：不新增映射 URL**
  - 路由形状不变（URL 中已是字符串段位，App.tsx 不依赖数字格式）
  - 前后端 ID 类型统一从 `int` 改为 `string/UUID`
  - 后端迁移期间同时接收 `int` 和 `uuid` 两种 `analysis_id`，不做额外映射 URL
  - 前端创建后按 string/UUID 跳转，不再做 `Number(id)` 转换

~~3. **`partial_ready` 状态的产品语义**：这个中间状态在前端是否有对应的 UI 表达？~~ → **已确认：是用户可见的正式状态，非内部态**
  - `partial_ready` = "核心结论已可读，但部分支撑数据/模块降级缺失"
  - UI 复用结果页，不单独开新页面
  - 展示"部分就绪 / 数据不完整"的 banner，对缺失模块做占位或降级提示
  - 不得伪装成完整结论，不得引导用户直接操作

~~4. **`user_actions` 表的 `action_type` 枚举字典**：在哪里维护？~~ → **已确认：独立常量文件，主维护点在 `structure/db_types.ts`**
  - 新增 `structure/action_types.ts` 作为项目级 action_type 枚举字典
  - `structure/db_types.ts` 补全 `UserActionType` 类型定义
  - 统一命名：`scenario_selected`、`analysis_submitted`、`behavior_intervention_shown`、`cooldown_started`、`review_task_completed`
  - 前后端各自跟随实现，不在表注释或页面中散落定义
