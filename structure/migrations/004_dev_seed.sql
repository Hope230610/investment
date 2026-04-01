-- ============================================
-- 开发/演示环境测试数据
-- 严禁在生产环境执行
-- ============================================

-- 插入示例用户（测试用）
INSERT INTO users (email, phone, hashed_password, is_active, signup_channel) VALUES
('test@example.com', '13800138000', '$2a$10$D28vCwFz9K3K5Z5X5V5B5C', TRUE, 'direct'),
('demo@example.com', '13800138001', '$2a$10$E39wDxF1L4L6M6Y6U6N6D', TRUE, 'referral')
ON CONFLICT (email) DO NOTHING;

-- 插入示例用户画像
INSERT INTO user_profiles (user_id, experience_level, holding_horizon, risk_tolerance, behavior_tags)
SELECT u.id, 'novice', 'medium', 'low', '{"chasing_rise"}'
FROM users u
WHERE u.email = 'test@example.com'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO user_profiles (user_id, experience_level, holding_horizon, risk_tolerance, behavior_tags)
SELECT u.id, 'intermediate', 'long', 'medium', '{"stable_discipline"}'
FROM users u
WHERE u.email = 'demo@example.com'
ON CONFLICT (user_id) DO NOTHING;
