# AI 投资决策系统 - 数据库设计文档

## 1. 数据库概述

- **数据库类型**: PostgreSQL 15+
- **字符集**: UTF8
- **排序规则**: zh_CN.UTF-8
- **设计原则**: 符合第三范式，支持 MVP 功能，预留扩展空间
- **UUID 方案**: 使用 `pgcrypto` 扩展提供的 `gen_random_uuid()`
- **种子数据策略**:
  - `002_init_data.sql` 仅保留生产可用的系统配置和基础股票数据
  - 开发/演示用户数据必须放入独立的 dev seed 文件，不进入生产初始化

## 2. 核心表结构

### 2.0 字段约束设计原则

除基础主键与时间字段外，当前阶段建议优先收紧以下约束：

- 所有枚举型字符串字段应限制在文档定义值范围内
- 自由文本字段优先控制长度，避免无限扩张
- JSONB 字段必须有固定结构说明，不允许“想到什么塞什么”
- 数组字段应限制元素枚举范围，并避免重复值
- 与产品边界强相关的字段必须可审计、可解释

### 2.1 用户表 (users)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 用户信息
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    hashed_password VARCHAR(255),

    -- 用户状态
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,

    -- 来源
    signup_channel VARCHAR(50) DEFAULT 'direct'
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
```

### 2.2 用户画像表 (user_profiles)

```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 画像字段（对应 types.ts）
    experience_level VARCHAR(20) NOT NULL DEFAULT 'novice',
    holding_horizon VARCHAR(20) NOT NULL DEFAULT 'medium',
    risk_tolerance VARCHAR(20) NOT NULL DEFAULT 'low',
    behavior_tags VARCHAR(50)[] NOT NULL DEFAULT '{}',

    -- 画像来源
    profile_source VARCHAR(20) NOT NULL DEFAULT 'user_input',

    UNIQUE(user_id)
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);

-- 注释
COMMENT ON COLUMN user_profiles.experience_level IS '新手: novice, 中级: intermediate, 有体系: expert';
COMMENT ON COLUMN user_profiles.holding_horizon IS '短期: short, 中期: medium, 长期: long';
COMMENT ON COLUMN user_profiles.risk_tolerance IS '低: low, 中: medium, 高: high';
COMMENT ON COLUMN user_profiles.behavior_tags IS '追涨: chasing_rise, 恐慌: panic_sell, 频繁: frequent_trading, 稳定: stable_discipline';
```

建议补充约束：

- `experience_level` 仅允许 `novice | intermediate | expert`
- `holding_horizon` 仅允许 `short | medium | long`
- `risk_tolerance` 仅允许 `low | medium | high`
- `behavior_tags` 元素仅允许：
  - `chasing_rise`
  - `panic_sell`
  - `frequent_trading`
  - `stable_discipline`
- `profile_source` 建议限制为：
  - `user_input`
  - `default_conservative`
  - `imported`

### 2.3 股票基础信息表 (stocks)

```sql
CREATE TABLE stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 股票标识
    stock_code VARCHAR(20) NOT NULL UNIQUE,
    stock_name VARCHAR(100) NOT NULL,

    -- 市场信息
    market VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    industry VARCHAR(100),
    sector VARCHAR(100),

    -- 状态
    is_listed BOOLEAN NOT NULL DEFAULT TRUE,
    list_date DATE,

    -- 搜索优化
    search_vector tsvector
);

CREATE UNIQUE INDEX idx_stocks_stock_code ON stocks(stock_code);
CREATE INDEX idx_stocks_market ON stocks(market);
CREATE INDEX idx_stocks_industry ON stocks(industry);
CREATE INDEX idx_stocks_search ON stocks USING GIN(search_vector);

-- 注释
COMMENT ON COLUMN stocks.market IS 'SH: 上海, SZ: 深圳, BJ: 北京';
COMMENT ON COLUMN stocks.exchange IS 'SSE: 上交所, SZSE: 深交所, BSE: 北交所';
```

建议补充约束：

- `stock_code` 不可为空，且建议按市场规则校验格式
- `market` 仅允许 `SH | SZ | BJ`
- `exchange` 仅允许 `SSE | SZSE | BSE`
- `stock_name` 建议限制最大长度 100

### 2.4 观察列表表 (watchlists)

```sql
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 关注信息
    focus_reason TEXT,
    added_from_scenario VARCHAR(50),
    source_analysis_id UUID,

    -- 提醒设置
    notify_on_events BOOLEAN DEFAULT TRUE,

    UNIQUE(user_id, stock_id)
);

CREATE INDEX idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX idx_watchlists_stock_id ON watchlists(stock_id);
```

建议补充约束：

- `added_from_scenario` 仅允许：
  - `single_stock_check`
  - `pre_trade_check`
  - `post_trade_review`
- `focus_reason` 建议限制最大长度 500 到 1000
- `source_analysis_id` 建议补外键到 `analysis_tasks(id)`，避免孤立引用

### 2.5 分析任务表 (analysis_tasks)

```sql
CREATE TABLE analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 场景信息
    scenario VARCHAR(30) NOT NULL,

    -- 任务状态
    status VARCHAR(20) NOT NULL DEFAULT 'processing',

    -- 输入数据快照
    user_profile_snapshot JSONB,
    scenario_payload JSONB,

    -- 时间戳
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ NOT NULL,

    -- 错误信息
    error_message TEXT
);

CREATE INDEX idx_analysis_tasks_user_id ON analysis_tasks(user_id);
CREATE INDEX idx_analysis_tasks_stock_id ON analysis_tasks(stock_id);
CREATE INDEX idx_analysis_tasks_scenario ON analysis_tasks(scenario);
CREATE INDEX idx_analysis_tasks_status ON analysis_tasks(status);
CREATE INDEX idx_analysis_tasks_expired_at ON analysis_tasks(expired_at);

-- 注释
COMMENT ON COLUMN analysis_tasks.scenario IS 'single_stock_check, pre_trade_check, post_trade_review';
COMMENT ON COLUMN analysis_tasks.status IS 'processing, partial_ready, ready, expired, failed';
```

建议补充约束：

- `scenario` 仅允许 `single_stock_check | pre_trade_check | post_trade_review`
- `status` 仅允许 `processing | partial_ready | ready | expired | failed`
- `error_message` 建议限制最大长度 1000
- `expired_at >= created_at`
- `completed_at >= started_at`

#### `user_profile_snapshot` JSON 结构规范

```json
{
  "experience_level": "novice",
  "holding_horizon": "medium",
  "risk_tolerance": "low",
  "behavior_tags": ["chasing_rise"],
  "profile_source": "user_input"
}
```

要求：

- 快照结构必须与用户画像核心字段保持一致
- 不应存储用户原始身份字段

#### `scenario_payload` JSON 结构规范

按场景分三类：

`single_stock_check`

```json
{
  "primary_horizon": "medium",
  "focus_reason": "关注估值和业绩稳定性"
}
```

`pre_trade_check`

```json
{
  "intent": "buy",
  "trigger_reason": "hot_topic",
  "emotion_level": 4,
  "original_plan": "回调后再观察"
}
```

`post_trade_review`

```json
{
  "action_taken": "sell",
  "trigger_reason": "panic_drop",
  "outcome_summary": "卖出后反弹",
  "emotion_level": 4,
  "plan_deviation": true
}
```

要求：

- `emotion_level` 建议限制为 `1-5`
- `intent` 建议限制为 `buy | add | reduce | sell`
- `focus_reason`、`original_plan`、`outcome_summary` 建议限制最大长度

### 2.6 分析结果表 (analysis_results)

```sql
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 六段式决策卡
    headline_judgement TEXT NOT NULL,
    key_reason_summary TEXT[] NOT NULL,
    user_fit_summary JSONB NOT NULL,
    next_step_actions TEXT[] NOT NULL,
    primary_risks TEXT NOT NULL,
    review_at TIMESTAMPTZ NOT NULL,

    -- 行为干预
    intervention JSONB,

    -- 适配性说明
    fit_summary TEXT,

    -- 市场背景
    market_context JSONB,

    -- AI 解释层
    explanation_layer JSONB,

    -- 详细推理
    detail_panels JSONB,

    -- 输出标记
    output_tags VARCHAR(50)[] NOT NULL DEFAULT '{}',

    -- 适配周期
    valid_period VARCHAR(20) NOT NULL DEFAULT 'medium'
);

CREATE UNIQUE INDEX idx_analysis_results_task_id ON analysis_results(analysis_task_id);

-- 注释
COMMENT ON COLUMN analysis_results.user_fit_summary IS '{fit: "适合谁", unfit: "不适合谁"}';
COMMENT ON COLUMN analysis_results.intervention IS '{behavior_type: "", severity: "", questions: []}';
COMMENT ON COLUMN analysis_results.market_context IS '{market_event: "", impact_boundary: ""}';
COMMENT ON COLUMN analysis_results.explanation_layer IS '{plain_text: "", case_example: ""}';
COMMENT ON COLUMN analysis_results.output_tags IS 'data_fact, model_inference, uncertainty';
```

建议补充约束：

- `headline_judgement` 建议限制最大长度 120
- `key_reason_summary` 建议限制为 1 到 5 条
- `next_step_actions` 建议限制为 1 到 3 条
- `valid_period` 仅允许 `short | medium | long`
- `output_tags` 元素仅允许：
  - `data_fact`
  - `model_inference`
  - `uncertainty`

#### `user_fit_summary` JSON 结构规范

```json
{
  "fit": "适合中期持有、风险偏好较低的用户参考",
  "unfit": "不适合短线冲动交易场景"
}
```

要求：

- 必须同时包含 `fit` 与 `unfit`
- 两字段都应为用户可读文本

#### `intervention` JSON 结构规范

```json
{
  "behavior_type": "chasing_rise",
  "severity": "high",
  "questions": [
    "这次动作是否偏离原计划？",
    "如果今天不操作，会失去什么？"
  ],
  "cooldown_minutes": 10,
  "trigger_reason": "hot_topic"
}
```

要求：

- `behavior_type` 仅允许 `chasing_rise | panic_sell | frequent_trading`
- `severity` 仅允许 `low | medium | high`
- `questions` 建议 1 到 5 条
- `cooldown_minutes` 建议为正整数

#### `market_context` JSON 结构规范

```json
{
  "market_event": "近期板块波动较大",
  "impact_boundary": "仅说明短期情绪影响，不代表趋势判断",
  "data_sources": ["quote", "announcement"]
}
```

#### `explanation_layer` JSON 结构规范

```json
{
  "plain_text": "用更通俗的话解释当前判断",
  "case_example": "类似先观察再验证，而不是立即行动"
}
```

#### `detail_panels` JSON 结构规范

```json
{
  "facts": ["估值水平处于历史中位附近"],
  "inferences": ["当前更适合等待更多验证信号"],
  "uncertainties": ["近期公告覆盖不完整"],
  "data_sources": ["quote", "announcement", "profile_snapshot"],
  "degrade_flags": ["missing_announcements"]
}
```

要求：

- 至少区分 `facts`、`inferences`、`uncertainties`
- `degrade_flags` 应与 API 返回保持一致

### 2.7 行为干预记录表 (behavior_interventions)

```sql
CREATE TABLE behavior_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_task_id UUID REFERENCES analysis_tasks(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 干预类型
    behavior_type VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,

    -- 冷静期
    cooldown_started_at TIMESTAMPTZ,
    cooldown_ended_at TIMESTAMPTZ,
    cooldown_questions TEXT[],

    -- 用户反馈
    user_acknowledged BOOLEAN DEFAULT FALSE,
    user_notes TEXT,

    -- 结果
    action_taken VARCHAR(50)
);

CREATE INDEX idx_behavior_interventions_user_id ON behavior_interventions(user_id);
CREATE INDEX idx_behavior_interventions_behavior_type ON behavior_interventions(behavior_type);
CREATE INDEX idx_behavior_interventions_created_at ON behavior_interventions(created_at);

-- 注释
COMMENT ON COLUMN behavior_interventions.behavior_type IS 'chasing_rise, panic_sell, frequent_trading';
COMMENT ON COLUMN behavior_interventions.severity IS 'low, medium, high';
```

建议补充约束：

- `behavior_type` 仅允许 `chasing_rise | panic_sell | frequent_trading`
- `severity` 仅允许 `low | medium | high`
- `action_taken` 建议限制为：
  - `continued`
  - `delayed`
  - `cancelled`
  - `logged_only`
- `cooldown_ended_at >= cooldown_started_at`

### 2.8 复盘任务表 (review_tasks)

```sql
CREATE TABLE review_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 复盘信息
    review_at TIMESTAMPTZ NOT NULL,
    scenario VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 复盘内容（完成后填写）
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,

    -- 归因分析
    attribution JSONB,
    improvement_actions TEXT[]
);

CREATE INDEX idx_review_tasks_user_id ON review_tasks(user_id);
CREATE INDEX idx_review_tasks_status ON review_tasks(status);
CREATE INDEX idx_review_tasks_review_at ON review_tasks(review_at);
CREATE UNIQUE INDEX idx_review_tasks_analysis_task_id ON review_tasks(analysis_task_id);

-- 注释
COMMENT ON COLUMN review_tasks.status IS 'pending, completed, expired';
COMMENT ON COLUMN review_tasks.attribution IS '{judgement_quality: "", execution_quality: "", luck_factor: ""}';
```

建议补充约束：

- `scenario` 仅允许 `single_stock_check | pre_trade_check | post_trade_review`
- `status` 仅允许 `pending | completed | expired`
- `review_notes` 建议限制最大长度 2000
- `reviewed_at >= created_at`

#### `attribution` JSON 结构规范

```json
{
  "judgement_quality": "medium",
  "execution_quality": "low",
  "luck_factor": "medium",
  "summary": "主要问题在执行而非初始判断"
}
```

要求：

- `judgement_quality`、`execution_quality`、`luck_factor` 建议统一枚举：
  - `low`
  - `medium`
  - `high`

### 2.9 用户操作记录表 (user_actions)

```sql
CREATE TABLE user_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 动作信息
    action_type VARCHAR(50) NOT NULL,
    action_payload JSONB,

    -- 关联
    stock_id UUID REFERENCES stocks(id),
    analysis_task_id UUID REFERENCES analysis_tasks(id),

    -- 来源
    page_path VARCHAR(255),
    user_agent TEXT
);

CREATE INDEX idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX idx_user_actions_action_type ON user_actions(action_type);
CREATE INDEX idx_user_actions_created_at ON user_actions(created_at);

-- 注释
COMMENT ON COLUMN user_actions.action_type IS 'scenario_selected, analysis_submitted, intervention_shown, review_completed等';
```

建议补充约束：

- `action_type` 应来自统一埋点字典
- `page_path` 建议限制最大长度 255
- `action_payload` 仅存最小必要字段，不得放敏感原文

### 2.10 系统配置表 (system_configs)

```sql
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_system_configs_key ON system_configs(config_key);
```

建议补充约束：

- `config_key` 使用固定 key 集合
- `config_value` 结构与 key 一一对应
- 高风险配置修改应进入审计

## 2.11 推荐检查约束清单

如果后续要把约束真正落库，建议优先补这些 `CHECK` 级规则：

- `user_profiles.experience_level`
- `user_profiles.holding_horizon`
- `user_profiles.risk_tolerance`
- `analysis_tasks.scenario`
- `analysis_tasks.status`
- `analysis_results.valid_period`
- `review_tasks.status`
- `behavior_interventions.severity`

这样可以先把最关键的枚举边界锁住。

## 3. 数据库视图

### 3.1 用户分析汇总视图

```sql
CREATE OR REPLACE VIEW v_user_analysis_summary AS
SELECT
    u.id AS user_id,
    COUNT(DISTINCT at.id) AS total_analyses,
    COUNT(DISTINCT CASE WHEN at.scenario = 'single_stock_check' THEN at.id END) AS single_stock_count,
    COUNT(DISTINCT CASE WHEN at.scenario = 'pre_trade_check' THEN at.id END) AS pre_trade_count,
    COUNT(DISTINCT CASE WHEN at.scenario = 'post_trade_review' THEN at.id END) AS post_trade_count,
    COUNT(DISTINCT bi.id) AS intervention_count,
    COUNT(DISTINCT CASE WHEN rt.status = 'completed' THEN rt.id END) AS completed_reviews,
    COUNT(DISTINCT wl.id) AS watchlist_count
FROM users u
LEFT JOIN analysis_tasks at ON u.id = at.user_id
LEFT JOIN behavior_interventions bi ON u.id = bi.user_id
LEFT JOIN review_tasks rt ON u.id = rt.user_id
LEFT JOIN watchlists wl ON u.id = wl.user_id
GROUP BY u.id;
```

### 3.2 待复盘任务视图

```sql
CREATE OR REPLACE VIEW v_pending_reviews AS
SELECT
    rt.id,
    rt.user_id,
    rt.analysis_task_id,
    s.stock_code,
    s.stock_name,
    rt.scenario,
    rt.review_at,
    rt.status,
    ar.headline_judgement,
    CASE
        WHEN rt.review_at < NOW() AND rt.status = 'pending' THEN 'expired'
        ELSE rt.status
    END AS display_status
FROM review_tasks rt
JOIN stocks s ON rt.stock_id = s.id
LEFT JOIN analysis_results ar ON rt.analysis_task_id = ar.analysis_task_id
WHERE rt.status IN ('pending', 'expired');
```

### 3.3 最近分析记录视图

```sql
CREATE OR REPLACE VIEW v_recent_analyses AS
SELECT
    at.id,
    at.user_id,
    at.scenario,
    at.stock_id,
    s.stock_code,
    s.stock_name,
    at.created_at,
    at.status,
    ar.headline_judgement
FROM analysis_tasks at
JOIN stocks s ON at.stock_id = s.id
LEFT JOIN analysis_results ar ON at.id = ar.analysis_task_id
WHERE at.status IN ('ready', 'expired')
ORDER BY at.created_at DESC;
```

## 4. 数据库函数与触发器

### 4.1 自动更新 updated_at

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 4.2 创建复盘任务触发器

```sql
CREATE OR REPLACE FUNCTION create_review_task()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO review_tasks (
        user_id,
        analysis_task_id,
        stock_id,
        review_at,
        scenario,
        status
    )
    SELECT
        at.user_id,
        at.id,
        at.stock_id,
        NEW.review_at,
        at.scenario,
        'pending'
    FROM analysis_tasks at
    WHERE at.id = NEW.analysis_task_id
    ON CONFLICT (analysis_task_id) DO NOTHING;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### 4.3 应用触发器

```sql
-- 为所有表添加 updated_at 触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_analysis_tasks_updated_at BEFORE UPDATE ON analysis_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建复盘任务触发器
CREATE TRIGGER trigger_create_review_task AFTER INSERT ON analysis_results
    FOR EACH ROW EXECUTE FUNCTION create_review_task();
```

## 5. 初始化数据

### 5.1 生产初始化数据

```sql
INSERT INTO system_configs (config_key, config_value, description) VALUES
('risk_warning_text', '"本系统为决策干预辅助，不提供直接买卖建议。所有分析基于模型推理，请结合市场实际情况判断。"', '风险提示文案'),
('cooldown_minutes', '10', '冷静期分钟数'),
('valid_periods', '{"short": 168, "medium": 720, "long": 2160}', '分析结论有效期（小时）'),
('max_recent_records', '20', '首页显示最近记录数'),
('default_stocks', '["600519", "000858", "601318"]', '默认股票列表'),
('analysis_timeout', '30000', '分析任务超时时间（毫秒）')
ON CONFLICT (config_key) DO NOTHING;
```

说明：

- 用户测试数据不应放入生产初始化脚本
- 如需本地联调演示，应使用单独 dev seed 文件

## 6. 索引优化建议

1. 定期分析查询模式，根据实际使用情况添加复合索引
2. 考虑对 analysis_tasks 和 user_actions 表进行分区（按时间）
3. 对 JSONB 字段的常用查询路径创建 GIN 索引

## 7. 数据迁移注意事项

1. 首次部署时按表依赖顺序执行：users → user_profiles → stocks → 其他表
2. 生产环境不得执行开发用户 seed
3. 股票数据和系统配置可作为基础初始化数据
4. 考虑使用数据库迁移工具（如 Flyway 或 Liquibase）
