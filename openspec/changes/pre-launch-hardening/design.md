## Context

当前代码经过 Gate 0（commit dd7eba3）修复后，已形成以下基线：

- **ResultPage.tsx**：confirm/dismiss 统一写 `feedback_dismissed_${id} = 'true'`，读端兼容旧的 `'confirmed'` 并归一化
- **profile_service.py**：upsert conflict target 从命名约束改为 `index_elements`，修复了 PostgreSQL 500
- **records.py**：new 分支三段拼接，graceful degradation
- **HomePage.tsx / RecordsPage.tsx**：入口切 `/api/v1/analysis`

在此基础上，以下三项尚未完全收口：

1. **Step2（PATCH /reviews/by-analysis/{id}）** 不是 upsert，查不到 ReviewTask 时返回 404，但前端 catch 块会将其静默标记为"卡片已处理"。用户看到成功，但 DB 里 review_tasks.status 未变。这是"假成功、真丢数"风险的最后一块。

2. **watchlist 三套语义**：前端真源 localStorage、后端 legacy 路径走 watchlist_items_legacy、record-reason 新路径写 watchlists。三套并存，一旦任何新功能读 `/api/v1/watchlist` 就会触发分裂。当前前端完全没调 `/api/v1/watchlist`，所以问题被 localStorage 遮住，但架构债务会随接入点增加而恶化。

3. **records/history 读源验证**：代码已改，但未在真实 DB 上验证过新表路径能返回有数据的记录，也未验证"结果未生成"时的 graceful degradation 行为。

## Goals / Non-Goals

**Goals：**
- confirm 链的两步（Step1 写画像 + Step2 更新 review task）均有明确成功/失败语义，前端不再将 Step2 失败静默标记为成功
- watchlist 确立单一服务端真源（watchlists 表），legacy 路径物理废弃但表暂保留
- records/history 新表路径在真实 DB 上可读、有数据、降级行为正确

**Non-Goals：**
- 不做 watchlist 的前端彻底服务端化（暂缓，换设备才触发）
- 不统一错误响应格式（前端已有 fallback，暂缓）
- 不做健康检查与监控（运维侧补）
- 不删除 watchlist_items_legacy 表（逻辑废弃，表暂保留）

## Decisions

### Decision 1: Step2 失败处理策略

**选项 A**：后端改 upsert（ReviewTask 不存在则创建）
- 优点：从根本上消除 404
- 缺点：改变了 ReviewTask 的生命周期语义（本来是 post_trade_review 创建才有，upsert 会让任意 analysis_task 都能有 ReviewTask）

**选项 B**：前端 catch 块区分错误类型并上报（不静默标记）
- 优点：不改变后端语义
- 缺点：前端需要区分 404（查不到 → 静默成功合理？）和其他错误（需要提示用户）

**选项 C（选这个）**：保留后端 404，在前端 catch 块中加日志和静默标记，但额外补一个"读端验证"机制——ResultPage 在关闭卡片后 500ms 读一次 `GET /api/v1/reviews?analysis_id={id}`，如果 status 未变则上报到结构化日志（不弹 toast，因为用户体验优先）
- 理由：Step2 404 的根因往往是 post_trade_review 页面没有正确触发 ReviewTask 创建（见 analysis_service.py:126）。这个问题更应该在创建端补足，而不是改更新语义。添加读端验证可以在不阻塞用户体验的情况下捕获静默失败。
- 替代方案：短期内先补 review_task 创建端的校验（process_analysis_v2 里已有兜底逻辑），再补读端验证

### Decision 2: watchlist 单一真源决策

**选项 A**：保留 legacy WatchlistService + watchlists 双写
- 优点：兼容旧调用
- 缺点：增加维护复杂度，split-brain 风险翻倍

**选项 B（选这个）**：legacy 路径逻辑废弃，watchlists 为唯一真源
- 不再向 `/api/v1/watchlist` 新增任何前端调用
- WatchlistService 代码保留但不维护，标记 `@deprecated`
- 后续 watchlist 功能全量走 record-reason 路径写入 + `/api/v1/analysis` 读回
- watchlist_items_legacy 表暂不删除，等后续迁移窗口处理

### Decision 3: confirm chain 自动化回归测试策略

在 `investment-front/src/utils/learningFeedback.test.ts` 中已有基础测试。需扩展：
- Mock Step1 返回成功，Step2 返回 404，验证 ResultPage 行为
- Mock 两步均成功，验证 DB 落库
- 不做完整的 HTTP E2E（后端已在其他测试覆盖），聚焦前端逻辑层

## Risks / Trade-offs

[Risk] Step2 的 ReviewTask 创建时机不稳定
→ Mitigation：process_analysis_v2（analysis.py:380-403）已有兜底创建逻辑，smoke 时重点验证 post_trade_review 场景下的 ReviewTask 是否存在

[Risk] watchlist 废弃后历史数据迁移
→ Mitigation：本 change 不做表删除，逻辑废弃后数据保留，后续迁移窗口再处理

[Risk] records.py new 分支在无数据时返回空列表，无法区分"真的没数据"和"查询失败"
→ Mitigation：在 records.py 返回前增加 `logger.debug("records_count", count=len(records))`，smoke 时检查日志确认路径走到了 new 分支

## Migration Plan

1. **smoke 验证阶段**（0.5 天）
   - 手动跑 confirm 链：登录 → post_trade_review → 反馈卡确认 → 检查 DB（emotion_history 有写入、review_tasks.status=completed）
   - 手动跑 records/history：打开记录页，确认有新表数据（非空列表）
   - 手动跑 watchlist record-reason：保存理由后，确认 watchlists 表有新记录

2. **代码收口阶段**（0.5 天）
   - reviews.py 读端验证补强（加日志）
   - ResultPage.tsx 读端验证（可选，取决于 smoke 结果）

3. **自动化回归阶段**（1 天）
   - 补 learningFeedback.test.ts 的 mock 测试
   - 覆盖 Step1 成功 + Step2 失败场景
   - 覆盖 Step1 + Step2 均成功场景

无回滚需求：所有变更均在现有 API 契约内，无破坏性变更。

## Open Questions

1. **Step2 404 的根因是 ReviewTask 创建时机问题，还是 Query 条件问题？** 探索阶段发现 reviews.py 按 `analysis_task_id + user_id` 查 ReviewTask，post_trade_review 场景下这个 id 是否正确传递？需在 smoke 时验证。

2. **watchlist record-reason 写入后，有没有读回路径？** 当前只有写入（analysis.py:656），但没有读 API 专门返回 watchlist 数据。后续如果要在 Profile 页展示"我的关注"，需要补 GET `/api/v1/watchlist` 的新实现（不走 legacy service），还是直接复用 analysis 表的 filter？这是下一个 change 要回答的问题。

3. **record-reason 422 场景是否已修？** Gate 0 commit 中 records.py 改了，但 `RecordReasonRequest` schema 是否在 analysis.py 里正确使用？需在 smoke 时验证 POST 一条 record-reason 是否出现 422。