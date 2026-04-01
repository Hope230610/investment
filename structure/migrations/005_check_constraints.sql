-- ============================================
-- 数据库 CHECK 约束迁移草案
-- 基于 investment_database_check_constraints_draft.md
-- 建议先在测试环境验证现有数据，再在生产环境执行
-- ============================================

-- ============================================
-- 1. user_profiles
-- ============================================
ALTER TABLE user_profiles
DROP CONSTRAINT IF EXISTS chk_user_profiles_experience_level;
ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_experience_level
CHECK (experience_level IN ('novice', 'intermediate', 'expert'));

ALTER TABLE user_profiles
DROP CONSTRAINT IF EXISTS chk_user_profiles_holding_horizon;
ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_holding_horizon
CHECK (holding_horizon IN ('short', 'medium', 'long'));

ALTER TABLE user_profiles
DROP CONSTRAINT IF EXISTS chk_user_profiles_risk_tolerance;
ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_risk_tolerance
CHECK (risk_tolerance IN ('low', 'medium', 'high'));

ALTER TABLE user_profiles
DROP CONSTRAINT IF EXISTS chk_user_profiles_profile_source;
ALTER TABLE user_profiles
ADD CONSTRAINT chk_user_profiles_profile_source
CHECK (profile_source IN ('user_input', 'default_conservative', 'imported'));

-- ============================================
-- 2. stocks
-- ============================================
ALTER TABLE stocks
DROP CONSTRAINT IF EXISTS chk_stocks_market;
ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_market
CHECK (market IN ('SH', 'SZ', 'BJ'));

ALTER TABLE stocks
DROP CONSTRAINT IF EXISTS chk_stocks_exchange;
ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_exchange
CHECK (exchange IN ('SSE', 'SZSE', 'BSE'));

ALTER TABLE stocks
DROP CONSTRAINT IF EXISTS chk_stocks_stock_name_length;
ALTER TABLE stocks
ADD CONSTRAINT chk_stocks_stock_name_length
CHECK (char_length(stock_name) BETWEEN 1 AND 100);

-- ============================================
-- 3. watchlists
-- ============================================
ALTER TABLE watchlists
DROP CONSTRAINT IF EXISTS chk_watchlists_added_from_scenario;
ALTER TABLE watchlists
ADD CONSTRAINT chk_watchlists_added_from_scenario
CHECK (
    added_from_scenario IS NULL
    OR added_from_scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review')
);

ALTER TABLE watchlists
DROP CONSTRAINT IF EXISTS chk_watchlists_focus_reason_length;
ALTER TABLE watchlists
ADD CONSTRAINT chk_watchlists_focus_reason_length
CHECK (
    focus_reason IS NULL
    OR char_length(focus_reason) <= 1000
);

-- ============================================
-- 4. analysis_tasks
-- ============================================
ALTER TABLE analysis_tasks
DROP CONSTRAINT IF EXISTS chk_analysis_tasks_scenario;
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_scenario
CHECK (scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review'));

ALTER TABLE analysis_tasks
DROP CONSTRAINT IF EXISTS chk_analysis_tasks_status;
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_status
CHECK (status IN ('processing', 'partial_ready', 'ready', 'expired', 'failed'));

ALTER TABLE analysis_tasks
DROP CONSTRAINT IF EXISTS chk_analysis_tasks_error_message_length;
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_error_message_length
CHECK (
    error_message IS NULL
    OR char_length(error_message) <= 1000
);

ALTER TABLE analysis_tasks
DROP CONSTRAINT IF EXISTS chk_analysis_tasks_expired_after_created;
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_expired_after_created
CHECK (expired_at >= created_at);

ALTER TABLE analysis_tasks
DROP CONSTRAINT IF EXISTS chk_analysis_tasks_completed_after_started;
ALTER TABLE analysis_tasks
ADD CONSTRAINT chk_analysis_tasks_completed_after_started
CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR completed_at >= started_at
);

-- ============================================
-- 5. analysis_results
-- ============================================
ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_headline_length;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_headline_length
CHECK (char_length(headline_judgement) BETWEEN 1 AND 120);

ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_reason_count;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_reason_count
CHECK (array_length(key_reason_summary, 1) BETWEEN 1 AND 5);

ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_next_step_count;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_next_step_count
CHECK (array_length(next_step_actions, 1) BETWEEN 1 AND 3);

ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_valid_period;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_valid_period
CHECK (valid_period IN ('short', 'medium', 'long'));

-- JSONB 弱约束
ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_user_fit_summary_keys;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_user_fit_summary_keys
CHECK (
    jsonb_typeof(user_fit_summary) = 'object'
    AND user_fit_summary ? 'fit'
    AND user_fit_summary ? 'unfit'
);

ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_intervention_object;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_intervention_object
CHECK (
    intervention IS NULL
    OR jsonb_typeof(intervention) = 'object'
);

ALTER TABLE analysis_results
DROP CONSTRAINT IF EXISTS chk_analysis_results_detail_panels_object;
ALTER TABLE analysis_results
ADD CONSTRAINT chk_analysis_results_detail_panels_object
CHECK (
    detail_panels IS NULL
    OR jsonb_typeof(detail_panels) = 'object'
);

-- ============================================
-- 6. behavior_interventions
-- ============================================
ALTER TABLE behavior_interventions
DROP CONSTRAINT IF EXISTS chk_behavior_interventions_behavior_type;
ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_behavior_type
CHECK (behavior_type IN ('chasing_rise', 'panic_sell', 'frequent_trading'));

ALTER TABLE behavior_interventions
DROP CONSTRAINT IF EXISTS chk_behavior_interventions_severity;
ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_severity
CHECK (severity IN ('low', 'medium', 'high'));

ALTER TABLE behavior_interventions
DROP CONSTRAINT IF EXISTS chk_behavior_interventions_action_taken;
ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_action_taken
CHECK (
    action_taken IS NULL
    OR action_taken IN ('continued', 'delayed', 'cancelled', 'logged_only')
);

ALTER TABLE behavior_interventions
DROP CONSTRAINT IF EXISTS chk_behavior_interventions_cooldown_time;
ALTER TABLE behavior_interventions
ADD CONSTRAINT chk_behavior_interventions_cooldown_time
CHECK (
    cooldown_started_at IS NULL
    OR cooldown_ended_at IS NULL
    OR cooldown_ended_at >= cooldown_started_at
);

-- ============================================
-- 7. review_tasks
-- ============================================
ALTER TABLE review_tasks
DROP CONSTRAINT IF EXISTS chk_review_tasks_scenario;
ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_scenario
CHECK (scenario IN ('single_stock_check', 'pre_trade_check', 'post_trade_review'));

ALTER TABLE review_tasks
DROP CONSTRAINT IF EXISTS chk_review_tasks_status;
ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_status
CHECK (status IN ('pending', 'completed', 'expired'));

ALTER TABLE review_tasks
DROP CONSTRAINT IF EXISTS chk_review_tasks_review_notes_length;
ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_review_notes_length
CHECK (
    review_notes IS NULL
    OR char_length(review_notes) <= 2000
);

ALTER TABLE review_tasks
DROP CONSTRAINT IF EXISTS chk_review_tasks_reviewed_after_created;
ALTER TABLE review_tasks
ADD CONSTRAINT chk_review_tasks_reviewed_after_created
CHECK (
    reviewed_at IS NULL
    OR reviewed_at >= created_at
);

-- ============================================
-- 8. user_actions
-- ============================================
ALTER TABLE user_actions
DROP CONSTRAINT IF EXISTS chk_user_actions_page_path_length;
ALTER TABLE user_actions
ADD CONSTRAINT chk_user_actions_page_path_length
CHECK (
    page_path IS NULL
    OR char_length(page_path) <= 255
);
