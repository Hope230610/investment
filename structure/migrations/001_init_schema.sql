-- ============================================
-- AI 投资决策系统 - 数据库初始化脚本
-- PostgreSQL 15+
-- ============================================

-- 启用 UUID 扩展（gen_random_uuid）
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- 1. 用户表
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    hashed_password VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    signup_channel VARCHAR(50) DEFAULT 'direct'
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);

-- ============================================
-- 2. 用户画像表
-- ============================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    experience_level VARCHAR(20) NOT NULL DEFAULT 'novice',
    holding_horizon VARCHAR(20) NOT NULL DEFAULT 'medium',
    risk_tolerance VARCHAR(20) NOT NULL DEFAULT 'low',
    behavior_tags VARCHAR(50)[] NOT NULL DEFAULT '{}',
    profile_source VARCHAR(20) NOT NULL DEFAULT 'user_input',
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);

COMMENT ON COLUMN user_profiles.experience_level IS '新手: novice, 中级: intermediate, 有体系: expert';
COMMENT ON COLUMN user_profiles.holding_horizon IS '短期: short, 中期: medium, 长期: long';
COMMENT ON COLUMN user_profiles.risk_tolerance IS '低: low, 中: medium, 高: high';

-- ============================================
-- 3. 股票基础信息表
-- ============================================
CREATE TABLE IF NOT EXISTS stocks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    stock_code VARCHAR(20) NOT NULL UNIQUE,
    stock_name VARCHAR(100) NOT NULL,
    market VARCHAR(10) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    industry VARCHAR(100),
    sector VARCHAR(100),
    is_listed BOOLEAN NOT NULL DEFAULT TRUE,
    list_date DATE,
    search_vector tsvector
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_stocks_stock_code ON stocks(stock_code);
CREATE INDEX IF NOT EXISTS idx_stocks_market ON stocks(market);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks(industry);
CREATE INDEX IF NOT EXISTS idx_stocks_search ON stocks USING GIN(search_vector);

COMMENT ON COLUMN stocks.market IS 'SH: 上海, SZ: 深圳, BJ: 北京';
COMMENT ON COLUMN stocks.exchange IS 'SSE: 上交所, SZSE: 深交所, BSE: 北交所';

-- ============================================
-- 4. 观察列表表
-- ============================================
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    focus_reason TEXT,
    added_from_scenario VARCHAR(50),
    source_analysis_id UUID,
    notify_on_events BOOLEAN DEFAULT TRUE,
    UNIQUE(user_id, stock_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlists_stock_id ON watchlists(stock_id);

-- ============================================
-- 5. 分析任务表
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    scenario VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    user_profile_snapshot JSONB,
    scenario_payload JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expired_at TIMESTAMPTZ NOT NULL,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_analysis_tasks_user_id ON analysis_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_stock_id ON analysis_tasks(stock_id);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_scenario ON analysis_tasks(scenario);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks(status);
CREATE INDEX IF NOT EXISTS idx_analysis_tasks_expired_at ON analysis_tasks(expired_at);

COMMENT ON COLUMN analysis_tasks.scenario IS 'single_stock_check, pre_trade_check, post_trade_review';
COMMENT ON COLUMN analysis_tasks.status IS 'processing, partial_ready, ready, expired, failed';

-- ============================================
-- 6. 分析结果表
-- ============================================
CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    headline_judgement TEXT NOT NULL,
    key_reason_summary TEXT[] NOT NULL,
    user_fit_summary JSONB NOT NULL,
    next_step_actions TEXT[] NOT NULL,
    primary_risks TEXT NOT NULL,
    review_at TIMESTAMPTZ NOT NULL,
    intervention JSONB,
    fit_summary TEXT,
    market_context JSONB,
    explanation_layer JSONB,
    detail_panels JSONB,
    output_tags VARCHAR(50)[] NOT NULL DEFAULT '{}',
    valid_period VARCHAR(20) NOT NULL DEFAULT 'medium'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_results_task_id ON analysis_results(analysis_task_id);

-- ============================================
-- 7. 行为干预记录表
-- ============================================
CREATE TABLE IF NOT EXISTS behavior_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_task_id UUID REFERENCES analysis_tasks(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    behavior_type VARCHAR(30) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    cooldown_started_at TIMESTAMPTZ,
    cooldown_ended_at TIMESTAMPTZ,
    cooldown_questions TEXT[],
    user_acknowledged BOOLEAN DEFAULT FALSE,
    user_notes TEXT,
    action_taken VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_behavior_interventions_user_id ON behavior_interventions(user_id);
CREATE INDEX IF NOT EXISTS idx_behavior_interventions_behavior_type ON behavior_interventions(behavior_type);
CREATE INDEX IF NOT EXISTS idx_behavior_interventions_created_at ON behavior_interventions(created_at);

COMMENT ON COLUMN behavior_interventions.behavior_type IS 'chasing_rise, panic_sell, frequent_trading';
COMMENT ON COLUMN behavior_interventions.severity IS 'low, medium, high';

-- ============================================
-- 8. 复盘任务表
-- ============================================
CREATE TABLE IF NOT EXISTS review_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_task_id UUID NOT NULL REFERENCES analysis_tasks(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    review_at TIMESTAMPTZ NOT NULL,
    scenario VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    attribution JSONB,
    improvement_actions TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_review_tasks_user_id ON review_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_review_tasks_status ON review_tasks(status);
CREATE INDEX IF NOT EXISTS idx_review_tasks_review_at ON review_tasks(review_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_review_tasks_analysis_task_id ON review_tasks(analysis_task_id);

COMMENT ON COLUMN review_tasks.status IS 'pending, completed, expired';

-- ============================================
-- 9. 用户操作记录表
-- ============================================
CREATE TABLE IF NOT EXISTS user_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action_type VARCHAR(50) NOT NULL,
    action_payload JSONB,
    stock_id UUID REFERENCES stocks(id),
    analysis_task_id UUID REFERENCES analysis_tasks(id),
    page_path VARCHAR(255),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_action_type ON user_actions(action_type);
CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions(created_at);

-- ============================================
-- 10. 系统配置表
-- ============================================
CREATE TABLE IF NOT EXISTS system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_system_configs_key ON system_configs(config_key);
