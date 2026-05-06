# AI 金融素养教练 - 后端

> 面向大学生的校园金融素养与决策辅助产品后端服务

## 技术栈

- **框架**: FastAPI - 现代、高性能的Web框架
- **异步处理**: ASGI + asyncio
- **数据库**: PostgreSQL 15+ + SQLAlchemy 2.0
- **验证**: Pydantic 2.x
- **日志**: Structlog + Python logging
- **测试**: pytest + httpx

## 项目结构

```
investment-back/
├── src/
│   ├── api/              # API路由
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py
│   │   │   ├── stocks.py
│   │   │   ├── watchlist.py
│   │   │   └── user.py
│   │   └── deps.py       # 依赖注入
│   ├── core/             # 核心配置
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── models/           # 数据库模型
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── stock.py
│   │   ├── analysis.py
│   │   └── watchlist.py
│   ├── schemas/          # Pydantic模式
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── stock.py
│   │   ├── watchlist.py
│   │   └── user.py
│   ├── services/         # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── analysis_service.py
│   │   ├── watchlist_service.py
│   │   └── user_service.py
│   ├── db/               # 数据库相关
│   │   ├── __init__.py
│   │   ├── session.py
│   │   └── init_db.py
│   └── utils/            # 工具函数
│       ├── __init__.py
│       └── helpers.py
├── alembic/              # 数据库迁移
│   ├── versions/
│   └── env.py
├── tests/                # 测试
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   └── test_services/
├── main.py               # 应用入口
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入你的配置
```

### 3. 初始化数据库

```bash
alembic upgrade head
```

### 4. 启动开发服务器

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看API文档。

## API 端点

### 分析相关
- `POST /api/v1/analysis` - 创建新的分析
- `GET /api/v1/analysis/{id}` - 获取分析结果
- `GET /api/v1/records` - 获取分析记录列表

### 金融产品风险评估
- `GET /api/v1/stocks/search?q=` - 搜索金融产品
- `GET /api/v1/stocks/{id}` - 获取金融产品详情

### 观察列表
- `GET /api/v1/watchlist` - 获取观察列表
- `POST /api/v1/watchlist` - 添加到观察列表
- `DELETE /api/v1/watchlist/{id}` - 从观察列表删除

### 用户相关
- `GET /api/v1/user/profile` - 获取用户画像
- `PUT /api/v1/user/profile` - 更新用户画像

## 开发指南

### 代码规范

- 使用类型提示（Type Hints）
- 遵循PEP 8规范
- 编写单元测试
- 使用有意义的变量和函数名

### 提交规范

- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- refactor: 重构
- test: 测试相关
- chore: 构建/工具相关

## 许可证

MIT License
