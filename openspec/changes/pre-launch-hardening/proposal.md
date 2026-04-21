## Why

当前代码在 Gate 0（commit dd7eba3）中已完成关键路径的修复，但这些修复尚未经过端到端验证，且存在两处尚未在代码中落地的架构决策：

1. **learning feedback confirm 链存在静默失败风险**。Step1 写 emotion_history/judgment_history，Step2 更新 ReviewTask.review_result + status。两步都成功才算真闭环，但 Step2 失败时前端仍会静默标记成功。ProfileService 已修（Step1），Step2 尚未专项验证。

2. **watchlist 存在三套语义分裂**。前端真源是 localStorage，后端 legacy 路径走 watchlist_items_legacy 表，record-reason 新路径写 watchlists 表。三套各自存在，互不感知，一旦任何新功能开始读 /api/v1/watchlist，就会触发分裂。

这两处如果不收口，内测用户会直接撞墙（假成功、真丢数 + 记录理由失踪），且随着前端接入点增加会越来越难修。

## What Changes

1. **learning feedback confirm 全链路验证 + Step2 补强**
   - 在 DB 层验证 Step1 + Step2 均落库（手动 smoke + 自动化回归）
   - Step2 不是 upsert：若 ReviewTask 不存在，当前返回 404 但前端静默吞掉。需在 reviews.py 补"未查到则跳过不报错"的容错行为，或在 ResultPage.tsx 的 catch 块里区分错误类型并上报
   - 补自动化回归测试，覆盖 confirm 全路径

2. **records/history 读源交叉验证**
   - 验证新表分支（analysis_tasks + analysis_results）能读到有结果的记录
   - 验证"结果未生成"场景下 graceful degradation 正常（headline=None，stock_name 回退"未知股票"）

3. **watchlist 架构决策 + 最小收口**
   - 正式确立：watchlists 表为服务端唯一真源，WatchlistService 标记为废弃路径，不再向前端新增 /api/v1/watchlist 调用
   - 在 review 任务的 reason 保存路径（POST /api/v1/analysis/{id}/record-reason）上补读回验证，确认写入后可被查询

4. **smoke checklist 固化**
   - 覆盖：登录、分析发起、结果页、learning feedback confirm（含 DB 验证）、记录页、Profile 页趋势区

## Capabilities

### New Capabilities

- `learning-feedback-confirm-chain`: 验证并修复 learning feedback 确认双写的端到端一致性。Step1 + Step2 均需落库，Step2 失败不能静默成功。此 capability 修复的是已有 spec 的实现差距，不新增 spec 行为。

- `watchlist-architectural-cleanup`: 消除 watchlist 的 split-brain 状态。确立 watchlists 表为服务端唯一真源，废弃 legacy WatchlistService 路径，补 record-reason 写入后的读回验证。

### Modified Capabilities

- `history-and-review-loop`: 无 requirement 变化，仅实现验证 + Step2 容错补强

## Impact

**受影响的执行板泳道：**
- 前端：ResultPage.tsx、HomePage.tsx、RecordsPage.tsx、ProfilePage.tsx
- 后端：reviews.py（Step2）、profile_service.py（已修）、records.py（已修，new 分支验证）
- 数据库：emotion_history、judgment_history、review_tasks 表的写路径验证

**关联的 structure 基线文档：**
- `structure/investment_current_implementation_gap_audit.md`（P0 Finding 3.1、3.2 已部分修复，本 change 完成剩余验证）
- `structure/investment_history_and_review_loop_design.md`（confirm 链端到端路径）
- `structure/investment_watchlist_focus_reason_design.md`（watchlist 架构决策依据）

**无破坏性变更**，本 change 全部在现有 API 契约内收口。