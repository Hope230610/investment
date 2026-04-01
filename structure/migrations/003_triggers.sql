-- ============================================
-- 数据库函数与触发器
-- ============================================

-- ============================================
-- 1. 自动更新 updated_at 字段的函数
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 2. 创建复盘任务的函数
-- ============================================
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

-- ============================================
-- 3. 检查结论是否过期的函数
-- ============================================
CREATE OR REPLACE FUNCTION check_conclusion_expiry()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.expired_at < NOW() AND NEW.status = 'ready' THEN
        NEW.status = 'expired';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- 4. 应用触发器
-- ============================================

-- 为所有表添加 updated_at 触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_stocks_updated_at ON stocks;
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_analysis_tasks_updated_at ON analysis_tasks;
CREATE TRIGGER update_analysis_tasks_updated_at BEFORE UPDATE ON analysis_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_system_configs_updated_at ON system_configs;
CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON system_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建复盘任务触发器
DROP TRIGGER IF EXISTS trigger_create_review_task ON analysis_results;
CREATE TRIGGER trigger_create_review_task AFTER INSERT ON analysis_results
    FOR EACH ROW EXECUTE FUNCTION create_review_task();

-- 检查分析任务过期触发器
DROP TRIGGER IF EXISTS trigger_check_expiry ON analysis_tasks;
CREATE TRIGGER trigger_check_expiry BEFORE UPDATE ON analysis_tasks
    FOR EACH ROW EXECUTE FUNCTION check_conclusion_expiry();

-- ============================================
-- 5. 创建视图
-- ============================================

-- 用户分析汇总视图
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

-- 待复盘任务视图
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
WHERE rt.status IN ('pending', 'expired')
ORDER BY rt.review_at ASC;

-- 最近分析记录视图
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
