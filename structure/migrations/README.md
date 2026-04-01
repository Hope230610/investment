# 数据库迁移说明

## 概述

本项目使用 PostgreSQL 15+ 作为数据库，包含以下迁移文件：

1. `001_init_schema.sql` - 创建所有表结构
2. `002_init_data.sql` - 插入生产可用初始数据（系统配置和基础股票数据）
3. `003_triggers.sql` - 创建数据库函数和触发器
4. `004_dev_seed.sql` - 可选，仅开发/演示环境使用的测试用户与画像数据
5. `005_check_constraints.sql` - 可选，补充稳定枚举、长度、时间关系和部分 JSONB 弱约束

## 执行迁移

### 方法一：使用 psql 命令

1. 连接到 PostgreSQL 数据库
2. 按顺序执行迁移文件

```bash
# 创建数据库（如果需要）
createdb -h localhost -U postgres ai_investment_system

# 执行第一个迁移（创建表结构）
psql -h localhost -U postgres -d ai_investment_system -f 001_init_schema.sql

# 执行第二个迁移（插入初始数据）
psql -h localhost -U postgres -d ai_investment_system -f 002_init_data.sql

# 执行第三个迁移（创建函数和触发器）
psql -h localhost -U postgres -d ai_investment_system -f 003_triggers.sql

# 如需本地演示测试用户，再额外执行（禁止在生产执行）
psql -h localhost -U postgres -d ai_investment_system -f 004_dev_seed.sql

# 如需启用数据库 CHECK 约束，再执行（建议先在测试环境验证现有数据）
psql -h localhost -U postgres -d ai_investment_system -f 005_check_constraints.sql
```

### 方法二：使用 pgAdmin

1. 打开 pgAdmin
2. 连接到数据库
3. 在 "工具" → "查询工具" 中打开每个文件
4. 按顺序执行

## 数据库连接配置

### 本地开发环境

```bash
# .env 文件示例
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_investment_system
DB_USER=postgres
DB_PASSWORD=123456
```
 
### Docker 部署

```dockerfile
# docker-compose.yml 示例
version: '3.8'
services:
  postgres:
    image: postgres:15
    container_name: ai_investment_db
    environment:
      POSTGRES_DB: ai_investment_system
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: yourpassword
    ports:
      - "5432:5432"
    volumes:
      - ./postgres_data:/var/lib/postgresql/data
      - ./migrations:/docker-entrypoint-initdb.d
```

## 数据备份与恢复

### 备份

```bash
pg_dump -h localhost -U postgres -d ai_investment_system -f backup.sql
```

### 恢复

```bash
psql -h localhost -U postgres -d ai_investment_system -f backup.sql
```

## 定期维护

### 1. 清理过期数据

```sql
-- 删除过期 30 天的分析任务
DELETE FROM analysis_tasks
WHERE expired_at < NOW() - INTERVAL '30 days';

-- 删除没有关联任务的结果
DELETE FROM analysis_results
WHERE analysis_task_id NOT IN (SELECT id FROM analysis_tasks);
```

### 2. 重建搜索索引

```sql
-- 更新搜索向量（在更新股票信息后）
UPDATE stocks
SET search_vector = to_tsvector('simple', stock_code || ' ' || stock_name || ' ' || industry || ' ' || sector);
```

### 3. 统计信息分析

```sql
-- ANALYZE 表格以优化查询计划
ANALYZE VERBOSE;
```

## 监控

### 慢查询日志配置

在 `postgresql.conf` 中添加：

```
log_min_duration_statement = 500ms  # 记录耗时超过 500ms 的查询
log_statement = 'mod'              # 记录数据修改语句
```

## 注意事项

1. 生产环境不得执行 `004_dev_seed.sql`
2. 定期备份重要数据
3. 避免在生产环境直接执行 SQL 文件
4. 使用连接池以提高性能
5. 若使用 `gen_random_uuid()`，需确保 `pgcrypto` 扩展已启用
6. 执行 `005_check_constraints.sql` 前，建议先检查现有数据是否满足约束

## 相关工具

- pgAdmin: 图形化数据库管理工具
- pgHero: 性能监控和优化工具
- Flyway: 数据库版本控制工具
