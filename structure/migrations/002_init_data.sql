-- ============================================
-- 生产初始化数据脚本
-- 仅保留系统配置和基础股票数据
-- 开发/演示用户请使用独立 dev seed 文件
-- ============================================

-- 插入系统配置
INSERT INTO system_configs (config_key, config_value, description) VALUES
('risk_warning_text', '"本系统为决策干预辅助，不提供直接买卖建议。所有分析基于模型推理，请结合市场实际情况判断。"', '页面风险提示文案'),
('cooldown_minutes', '10', '高风险场景冷静期分钟数'),
('valid_periods', '{"short": 168, "medium": 720, "long": 2160}', '分析结论有效期（小时）'),
('max_recent_records', '20', '首页显示最近记录数'),
('default_stocks', '["600519", "000858", "601318"]', '默认股票列表'),
('analysis_timeout', '30000', '分析任务超时时间（毫秒）')
ON CONFLICT (config_key) DO NOTHING;

-- 插入示例股票数据
INSERT INTO stocks (stock_code, stock_name, market, exchange, industry, sector) VALUES
('600519', '贵州茅台', 'SH', 'SSE', '白酒', '食品饮料'),
('000858', '五粮液', 'SZ', 'SZSE', '白酒', '食品饮料'),
('601318', '中国平安', 'SH', 'SSE', '保险', '金融'),
('000001', '平安银行', 'SZ', 'SZSE', '银行', '金融'),
('000002', '万科A', 'SZ', 'SZSE', '房地产', '房地产'),
('600036', '招商银行', 'SH', 'SSE', '银行', '金融'),
('600276', '恒瑞医药', 'SH', 'SSE', '化学制药', '医药生物'),
('002594', '比亚迪', 'SZ', 'SZSE', '汽车整车', '汽车'),
('300059', '东方财富', 'SZ', 'SZSE', '证券', '金融'),
('600031', '三一重工', 'SH', 'SSE', '工程机械', '机械设备')
ON CONFLICT (stock_code) DO NOTHING;
