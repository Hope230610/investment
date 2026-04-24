## Context

当前观察列表能力处于“模型已迁移、接口未迁移”的分裂状态：

- `investment-back/src/api/v1/watchlist.py` 仍通过 `WatchlistService` 读写 `watchlist_items_legacy`
- `investment-back/src/schemas/watchlist.py` 中 `WatchlistItem` 仍是 `int` ID，且缺少 `stock_name`、`market`、`industry`
- `investment-back/src/api/v1/analysis.py` 的 `POST /api/v1/analysis/{id}/record-reason` 在 UUID 路径下已经写入 `watchlists` v2，并具备 `user_id + stock_id` upsert 语义
- `investment-front/src/types.ts` 与页面展示依赖 UUID 风格 `id`、股票摘要字段和 `focus_reason`，当前仍靠 `localStorage` 兜底

这意味着同一能力已经存在两套“真相”：

1. 专用 watchlist API 读写 legacy 表
2. 分析结果页 `record-reason` 写入 v2 表

如果继续推进 B1b 前端切换，而不先收口 B1a，前端将会接入错误数据源，产生可见的数据分裂。

约束与前提：

- 本次 change 目标是 P1 收口，不引入新的产品能力
- 不修改数据库连接设置，不引入新外部依赖
- 当前仓库中 `Watchlist` v2 模型、`watchlists` 迁移和 `added_from_scenario` 枚举规范化迁移已经存在，应优先复用
- 当前代码层面的 `user_id` 仍为 `Integer`、`stock_id` 仍为字符串标识；这与部分 `structure` 文档中的更远期 UUID 设计不完全一致，但不在本次改造范围

## Goals / Non-Goals

**Goals:**

- 将 `/api/v1/watchlist` 的 list/add/update/delete 全部切换到 `watchlists` v2
- 为观察列表冻结一份稳定的 v2 API 契约：UUID 标识 + 股票展示字段 + 统一时间字段语义
- 让 `/api/v1/watchlist` 与 `POST /api/v1/analysis/{id}/record-reason` 共享同一套 upsert / update / remove 规则
- 停止专用 watchlist API 对 legacy 表的任何新增写入
- 为 B1b 前端切换提供明确的接口、迁移和验收前提

**Non-Goals:**

- 不在本次 change 中切换前端页面到新 API
- 不移除 `localStorage` helper；该动作属于后续 B1b
- 不在本次 change 中解决全局 `users` / `stocks` 主键类型与长文档基线的全部差异
- 不实现观察列表分页、事件提醒规则或通知下发
- 不强制移除整数 `analysis_id` 的旧兼容路径，除非实现时确认其已无调用方且不会影响现有链路

## Decisions

### 决策 1：保留 `/api/v1/watchlist` 路径，替换其内部实现为 v2

我们保留现有路由路径，不新增 `/api/v1/watchlists` 或其他别名路径。这样可以把变更集中在契约升级而不是路径迁移，降低 B1b 前端切换成本，也避免同时处理“路径改名”和“数据源改造”两类变化。

选择理由：

- 当前前端和文档都已围绕 `/api/v1/watchlist` 建立认知
- 真实问题是路径背后的数据源和响应结构错误，而不是路径本身
- 保留路径更适合做一次“内部换引擎”的收口

放弃的替代方案：

- 新开 `/api/v1/watchlists`：会让 B1b 同时承受路径替换和契约替换，收益不高
- 完全依赖 `GET /api/v1/analysis` 过滤查询：读路径可以凑合，但 add/update/remove 仍缺专用接口，不利于前端页面闭环

### 决策 2：以单一 v2 服务层承接 watchlist API 与 `record-reason`

当前 `record-reason` 的 UUID 路径已经拥有正确的 v2 upsert 语义，因此 B1a 不应重新发明一套平行逻辑。我们会把 v2 观察列表的核心操作收口到一个服务层中，由它负责：

- 查询用户观察列表并联表返回 `stocks` 摘要字段
- 基于 `user_id + stock_id` 执行 upsert
- 按 UUID 更新 `focus_reason`
- 按 UUID 删除观察项
- 在需要时写入 `added_from_scenario`、`source_analysis_id`、`notify_on_events`

`/api/v1/watchlist` 与 `POST /api/v1/analysis/{id}/record-reason` 都调用同一服务层能力，避免再次产生“双实现、双语义”。

选择理由：

- 当前分裂的根因不是路由，而是写路径落在两套表和两段逻辑里
- 服务层复用比在路由层互相调用更清晰，也更易测试
- 后续 B1b 和提醒能力都需要稳定的服务端领域语义

放弃的替代方案：

- 直接在 `watchlist.py` 中复制 `_add_watchlist_from_new_path` 逻辑：短期快，但会把分裂从“表分裂”变成“代码分裂”
- 让 `watchlist.py` 直接导入 `analysis.py` 的私有 helper：耦合方向错误，后续维护成本高

### 决策 3：观察列表响应契约以 UUID + 股票摘要 + 后端标准时间字段为准

本次 API 契约将以 v2 结构为准，`id` 统一为 UUID 字符串，并通过联表 `stocks` 返回 `stock_name`、`market`、`industry`。时间字段优先沿用后端当前通用命名 `created_at` / `updated_at`，而不是为单一页面额外引入数据库层没有的 `added_at`。

选择理由：

- `created_at` / `updated_at` 已在后端 schema 体系中广泛存在，成本最低
- 前端对 `added_at` 的需求本质是展示语义，B1b 可以在 API 调用层做一次映射
- 如果本次后端为了单一页面引入 `added_at` 别名，会让 watchlist 契约与其他资源契约更加割裂

放弃的替代方案：

- 直接在 API 返回 `added_at`：前端更省事，但会扩大后端契约不一致
- 同时返回 `created_at` 和 `added_at`：兼容性高，但会引入重复字段和长期维护噪音

### 决策 4：legacy 表保留为只读遗留资产，不做双写

本次变更不会删除 `watchlist_items_legacy` / `focus_reasons_legacy`，但 `/api/v1/watchlist` 不再向它们写入新数据，也不做 v2 → legacy 双写。legacy 表仅作为回溯和应急参考存在。

选择理由：

- 双写会把“当前已知的双数据源问题”固化为长期机制
- B1a 的目的就是收口真源，而不是延长过渡态
- 当前 `record-reason` 已经在 UUID 路径写入 v2，继续双写只会让一致性更难验证

放弃的替代方案：

- 双写 legacy 与 v2：会增加回滚表象上的安全感，但会把去重、幂等和故障定位复杂度翻倍
- 立即删除 legacy 模型与表：风险过高，不适合作为本次 P1 收口动作

### 决策 5：watchlist 路由切到统一错误结构与结构化日志

当前 `watchlist.py` 仍主要通过 `HTTPException(detail=...)` 返回错误，这与项目正在推进的统一错误契约不一致。B1a 中 watchlist 路由应返回与 `analysis.py` 一致的 `{ error: { code, message, request_id, retryable } }` 结构，并记录结构化日志字段，例如 `user_id`、`stock_id`、`watchlist_id`、`path_source`。

选择理由：

- B1b 前端切换时需要稳定解析错误，而不是继续兼容局部特例
- 观察列表是 P1 主链路，错误模型不应继续落后于分析接口
- 结构化日志有助于排查幂等冲突、联表异常和权限问题

放弃的替代方案：

- 保持 `HTTPException` 不变：实现快，但会把 watchlist 继续留在旧错误模型
- 顺手重构全项目错误辅助函数：收益更大，但超出本次变更范围

### 决策 6：优先复用现有迁移，不默认新增数据库 schema 变更

从仓库现状看，`004_migrate_watchlists.py` 已创建 `watchlists`，`010_normalize_watchlist_added_from_scenario_enum.py` 已规范化枚举值。本次 change 默认假设数据库结构已具备，只在实现中发现“代码模型与 Alembic head 不一致、且会阻塞接口正确性”时再追加最小迁移。

选择理由：

- 当前问题主要是应用层没有接入 v2，而不是表不存在
- 先减少 schema 变量，便于快速验证 API 收口
- 若把实现问题误判成 schema 问题，会扩大改造面

放弃的替代方案：

- 预先追加新迁移：在未确认缺口前引入不必要的数据库变化
- 忽略 schema 校验：可能导致代码按 v2 写，但部署环境缺字段或枚举异常

## Risks / Trade-offs

- [隐藏调用方兼容性风险] `id` 从 `int` 升级为 UUID 字符串后，任何仍依赖旧契约的调用方都会受影响 → Mitigation：在 proposal/spec 中明确标记 BREAKING，补 list/add/update/delete 与错误响应测试，并尽快衔接 B1b
- [双源尾巴风险] 旧的整数 `analysis_id` 兼容路径仍可能继续写 legacy `focus_reasons_legacy` → Mitigation：B1a 聚焦专用 watchlist API 与 UUID 主路径收口，同时为 legacy 分支补日志告警，后续单独评估是否彻底移除
- [联表数据完整性风险] 若 `stocks` 记录缺失或字段为空，观察列表响应会缺股票展示字段 → Mitigation：新增/更新时校验 `stock_id`，列表查询对缺失字段给出显式空值策略，并补联表测试
- [回滚语义不对称] 代码回滚到 legacy 实现后，用户会再次看到“专用 API 不显示 v2 新数据”的旧问题 → Mitigation：把本次上线视为前进式切换，优先选择前滚修复而不是长期回退到旧实现
- [错误模型仍局部收口] 仅 watchlist 路由采用统一错误结构，其他旧路由仍可能保留 `detail` 风格 → Mitigation：本次至少保证 B1b 依赖的 watchlist 链路一致，并把全局错误模型统一继续留在更大的 API 收口工作中

## Migration Plan

1. 先确认部署环境已经包含 `watchlists` 表、唯一约束和 `added_from_scenario` 枚举规范化结果；若与 Alembic head 不一致，先修复环境或补最小迁移。
2. 重构后端 schema 与 service，使 `/api/v1/watchlist` 全量走 v2，并让 `record-reason` 的 UUID 路径委托到同一服务层。
3. 将 watchlist 路由改为统一错误结构与 UUID 参数语义，补齐 `stock_name`、`market`、`industry` 返回。
4. 执行接口级 smoke：`GET /api/v1/watchlist`、`POST /api/v1/watchlist`、`PUT /api/v1/watchlist/{uuid}`、`DELETE /api/v1/watchlist/{uuid}`、`POST /api/v1/analysis/{uuid}/record-reason`。
5. 输出冻结后的契约与联调要点，作为后续 B1b 的输入。

回滚策略：

- 若问题发生在部署前的开发验证阶段，直接回退代码即可，因为 legacy 表仍保留
- 若问题发生在已开始使用 v2 接口之后，优先前滚修复；单纯回退到 legacy 代码虽然不会删除 v2 数据，但会重新暴露“专用 API 看不到新数据”的行为回退

## Open Questions

- B1a 是否只返回 `created_at` / `updated_at`，还是为了前端过渡额外补一个 `added_at` 只读别名？当前设计默认只返回后端标准时间字段。
- 整数 `analysis_id` 的 `record-reason` 兼容分支是否还有真实调用方？如果没有，后续可以单独提变更移除 legacy `focus_reasons_legacy` 写路径。
