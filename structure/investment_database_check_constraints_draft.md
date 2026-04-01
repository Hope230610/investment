# AI 投资决策助手 数据库 CHECK 约束草案

更新时间：2026-03-30

## 1. 文档目的

本草案用于把 [database_design.md](F:/investment/structure/database_design.md) 中已经明确的字段约束，进一步下沉为可执行的 SQL 级 `CHECK` 约束方案。

目标不是一次性把所有约束都强行落库，而是先明确：

- 哪些约束适合直接落到数据库
- 哪些约束更适合继续停留在应用层
- 哪些 JSONB 字段适合先做弱约束，后续再做强校验

## 2. 约束落地原则

- 对稳定枚举优先使用数据库 `CHECK`
- 对时间前后关系优先使用数据库 `CHECK`
- 对字符串长度可用数据库 `CHECK` 做兜底
- 对复杂 JSONB 结构，当前阶段优先在应用层校验，不建议一开始在数据库中写过重约束
- 对未来可能频繁变化的业务枚举，不建议过早写死在数据库

## 3. 建议优先落库的 P0 约束

### 3.1 `user_profiles`

```sql
ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_experience_level
CHECK (experience_level IN ('novice', 'intermediate', 'expert'));

ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_holding_horizon
CHECK (holding_horizon IN ('short', 'medium', 'long'));

ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_risk_tolerance
CHECK (risk_tolerance IN ('low', 'medium', 'high'));

ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_profile_source
CHECK (profile_source IN ('user_input', 'default_conservative', 'imported'));
```

说明：

- 这几组枚举非常稳定，适合直接锁死
- `behavior_tags` 为数组，当前阶段不建议直接用复杂表达式做强校验，可先由应用层保证

### 3.2 `stocks`

```sql
ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_market
CHECK (market IN ('SH', 'SZ', 'BJ'));

ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_exchange
CHECK (exchange IN ('SSE', 'SZSE', 'BSE'));

ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_stock_name_length
CHECK (char_length(stock_name) BETWEEN 1 AND 100);
```

### 3.3 `watchlists`

```sql
ALTER TABLE watchlists
ADD CONSTRAINT chk_watchlists_added_from_scenario
CHECK (
    added_from_scenario IS NULL
    OR added_from_scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review')
);

ALTER TABLE watchlists
ADD CONSTRAINT chk_watchlists_focus_reason_length
CHECK (
    focus_reason IS NULL
    OR char_length(focus_reason) <= 1000
);
```

### 3.4 `analysis_tasks`

```sql
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_scenario
CHECK (scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review'));

ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_status
CHECK (status IN ('processing', 'partial_ready', 'ready', 'expired', 'failed'));

ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_error_message_length
CHECK (
    error_message IS NULL
    OR char_length(error_message) <= 1000
);

ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_expired_after_created
CHECK (expired_at >= created_at);

ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_completed_after_started
CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR completed_at >= started_at
);
```

### 3.5 `analysis_results`

```sql
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_headline_length
CHECK (char_length(headline_judgement) BETWEEN 1 AND 120);

ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_reason_count
CHECK (array_length(key_reason_summary, 1) BETWEEN 1 AND 5);

ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_next_step_count
CHECK (array_length(next_step_actions, 1) BETWEEN 1 AND 3);

ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_valid_period
CHECK (valid_period IN ('short', 'medium', 'long'));
```

说明：

- `output_tags` 当前阶段建议继续由应用层校验元素值
- `review_at` 是否一定大于创建时间，要看业务是否允许回补历史数据；当前先不强加数据库约束

### 3.6 `behavior_interventions`

```sql
ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_behavior_type
CHECK (behavior_type IN ('chasing_rise', 'panic_sell', 'frequent_trading'));

ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_severity
CHECK (severity IN ('low', 'medium', 'high'));

ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_action_taken
CHECK (
    action_taken IS NULL
    OR action_taken IN ('continued', 'delayed', 'cancelled', 'logged_only')
);

ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_cooldown_time
CHECK (
    cooldown_started_at IS NULL
    OR cooldown_ended_at IS NULL
    OR cooldown_ended_at >= cooldown_started_at
);
```

### 3.7 `review_tasks`

```sql
ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_scenario
CHECK (scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review'));

ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_status
CHECK (status IN ('pending', 'completed', 'expired'));

ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_review_notes_length
CHECK (
    review_notes IS NULL
    OR char_length(review_notes) <= 2000
);

ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_reviewed_after_created
CHECK (
    reviewed_at IS NULL
    OR reviewed_at >= created_at
);
```

### 3.8 `user_actions`

```sql
ALTER TABLE user_actions
ADD CONSTRAINT chk_user_actions_page_path_length
CHECK (
    page_path IS NULL
    OR char_length(page_path) <= 255
);
```

## 4. 建议保留在应用层的约束

以下约束当前不建议直接写进数据库：

- `behavior_tags` 数组元素合法性
- `output_tags` 数组元素合法性
- `scenario_payload` 的场景分支结构
- `user_profile_snapshot` 的完整结构
- `intervention`、`market_context`、`detail_panels`、`attribution` 的 JSON 字段完整性

原因：

- 用纯 SQL 校验 JSONB 会显著增加复杂度
- 当前产品仍在快速迭代，过早把 JSON 结构写死会增加迁移成本

## 5. JSONB 弱约束建议

如果后续希望数据库也对 JSONB 做最低限度约束，建议先做“存在性弱约束”。

### 5.1 `analysis_results.user_fit_summary`

```sql
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_user_fit_summary_keys
CHECK (
    jsonb_typeof(user_fit_summary) = 'object'
    AND user_fit_summary ? 'fit'
    AND user_fit_summary ? 'unfit'
);
```

### 5.2 `analysis_results.intervention`

```sql
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_intervention_object
CHECK (
    intervention IS NULL
    OR jsonb_typeof(intervention) = 'object'
);
```

### 5.3 `analysis_results.detail_panels`

```sql
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_detail_panels_object
CHECK (
    detail_panels IS NULL
    OR jsonb_typeof(detail_panels) = 'object'
);
```

说明：

- 这里只校验“是否是对象”和“关键键是否存在”
- 不建议一开始做过重的 JSON 路径检查

## 6. 推荐迁移顺序

建议新增一个单独迁移，例如：

- `005_check_constraints.sql`

顺序：

1. 先添加最稳定的枚举约束
2. 再添加时间和长度约束
3. 最后再考虑 JSONB 弱约束

## 7. 上线前优先级建议

### P0

- `user_profiles` 枚举约束
- `analysis_tasks` 状态与时间约束
- `analysis_results` 标题/数组数量/有效期约束
- `review_tasks` 状态约束
- `behavior_interventions` 严重级别与行为类型约束

### P1

- `watchlists` 文本长度和来源场景约束
- `user_actions` 路径长度约束
- JSONB 弱约束

### P2

- 数组元素合法性数据库校验
- 更严格的 JSON 路径级校验

## 8. 风险与取舍

### 好处

- 把一部分脏数据挡在数据库层
- 让前后端错误更早暴露
- 避免状态枚举逐步漂移

### 风险

- 如果现有数据已经不干净，直接加约束会失败
- 如果产品字段仍频繁调整，数据库约束会增加迁移频率

因此建议：

- 先在测试环境验证现有数据是否满足约束
- 再逐批引入

## 9. 最终结论

数据库约束不应该替代应用层校验，但应该承担“稳定边界的最后一道门”。

当前最适合先落库的是：

- 枚举
- 时间前后关系
- 文本长度

而复杂 JSON 结构，当前仍建议由应用层和类型定义主导。
