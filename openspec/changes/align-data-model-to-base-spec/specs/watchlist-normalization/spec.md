## Purpose

定义规范化观察列表的数据结构，将原有的 `watchlist_items` 和 `focus_reasons` 两表合并为单一 `watchlists` 表，消除多表关联带来的查询复杂性。

## Requirements

### Requirement: 观察列表必须以股票为维度去重
系统 SHALL 以用户 + 股票为唯一约束（`UNIQUE(user_id, stock_id)`）维护观察列表，同一用户对同一股票不得重复添加。

#### Scenario: 用户重复添加同一只股票
- **WHEN** 用户尝试将已在观察列表中的股票再次添加
- **THEN** 系统返回 409 冲突，不创建重复记录

### Requirement: 观察理由必须与场景关联
系统 SHALL 在添加观察时记录关注理由和来源场景（`single_stock_check / pre_trade_check / post_trade_review`），并可选关联来源分析任务 ID。

#### Scenario: 从单股咨询结果添加观察
- **WHEN** 用户在单股咨询结果页点击"加入观察"
- **THEN** 系统在 `watchlists` 中保存 `focus_reason`、`added_from_scenario = "single_stock_check"` 和可选 `source_analysis_id`

### Requirement: 观察列表必须支持事件提醒开关
系统 SHALL 支持用户开关单只股票的事件提醒（`notify_on_events`），默认开启。

#### Scenario: 用户关闭单只股票的事件提醒
- **WHEN** 用户在观察列表中将某只股票的提醒关闭
- **THEN** 系统更新该记录的 `notify_on_events = false`，后续事件通知跳过该股票
