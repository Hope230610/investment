# 项目落地指南

本文档详细描述了如何将 AI 投资决策系统从开发状态部署到可运行状态。

---

## 🔧 已完成的修改

### 1. 项目文档修正
- **文件**：`PROJECT_README.md`
- **变更**：明确技术栈为 Python + FastAPI，修正架构图和启动说明

### 2. 启动脚本重写
- **文件**：`start.bat`
- **变更**：
  - 支持 Python 依赖安装和启动
  - 统一数据库配置
  - 修复前端端口配置（Vite 开发服务器默认 5173）

### 3. 前端 API 代理配置
- **文件**：`investment-front/vite.config.ts`
- **变更**：
  - 添加代理配置 `/api` → `http://localhost:8000`
  - 支持跨域请求

### 4. 环境变量配置
- **文件**：`investment-back/.env` 和 `investment-front/.env`
- **变更**：统一数据库配置为：
  - 数据库：investment_db
  - 用户：postgres
  - 密码：123456

### 5. 认证机制简化
- **文件**：`investment-back/src/api/deps.py`
- **变更**：开发模式下自动创建和返回测试用户（无需登录）

### 6. 缺失 API 接口补充
- **文件**：
  - `investment-back/src/api/v1/reviews.py` - 获取待复盘任务接口
  - `investment-back/src/api/v1/records.py` - 获取分析记录接口
- **变更**：补充了前端所需的路由

### 7. API 路由注册
- **文件**：`investment-back/src/api/v1/__init__.py`
- **变更**：添加 reviews 和 records 路由

---

## 🚀 部署步骤

### 1. 系统要求

**Windows 环境：**
- Node.js 18+
- Python 3.9+
- PostgreSQL 15+

**依赖：**
- pgAdmin 或其他数据库管理工具
- 命令提示符（以管理员身份运行）

### 2. 数据库初始化

#### 2.1 创建数据库
```sql
CREATE DATABASE investment_db;
```

#### 2.2 执行初始化脚本
在 pgAdmin 中执行以下 SQL 脚本（顺序执行）：
1. `structure/migrations/001_init_schema.sql` - 创建表结构
2. `structure/migrations/002_init_data.sql` - 插入示例数据
3. `structure/migrations/003_triggers.sql` - 创建触发器和视图

### 3. 项目启动

#### 3.1 使用启动脚本（推荐）
以 **管理员身份** 运行 `start.bat`：

```bash
cd f:\investment
start.bat
```

选择操作：
- **1. 完整启动** - 安装依赖 + 初始化数据库 + 启动服务
- **2. 快速启动** - 直接启动服务（已安装依赖）
- **3. 仅安装依赖** - 只安装前后端依赖

#### 3.2 手动启动（备用方案）

**后端启动：**
```bash
cd investment-back
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**前端启动：**
```bash
cd investment-front
npm install
npm run dev
```

### 4. 访问地址

启动后可访问：
- **前端应用**：http://localhost:5173
- **后端 API 文档**：http://localhost:8000/api/v1/docs
- **健康检查**：http://localhost:8000/health

### 5. 测试用户

系统在开发模式下会自动创建测试用户：
- 用户名：testuser
- 密码：testpassword123
- 角色：默认用户（新手级）

---

## 📊 系统架构

### 核心组件
- **前端**：React 19 + TypeScript + Vite + Tailwind CSS
- **后端**：FastAPI + SQLAlchemy 2.0 + PostgreSQL
- **认证**：JWT Token（开发模式简化）
- **数据库**：PostgreSQL 15+

### API 接口
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/user/profile` | 获取用户画像 |
| PUT | `/api/v1/user/profile` | 更新用户画像 |
| GET | `/api/v1/stocks/search` | 搜索股票 |
| POST | `/api/v1/analysis` | 创建分析任务 |
| GET | `/api/v1/analysis/:id` | 获取分析结果 |
| GET | `/api/v1/reviews` | 获取待复盘任务 |
| GET | `/api/v1/records` | 获取分析记录 |

---

## 🔍 功能验证

### 验证步骤

1. **页面加载**：访问 http://localhost:5173
2. **首页功能**：
   - 查看用户画像摘要（系统自动创建）
   - 查看三个分析场景
3. **股票搜索**：点击任意场景 → 搜索股票
4. **创建分析**：
   - 选择单股咨询 → 输入股票代码（如 SH600519）
   - 系统会生成模拟分析结果
5. **查看记录**：点击"记录"页面

### 预期结果

- 所有页面可正常加载
- API 请求返回 200 状态码
- 股票搜索功能正常工作
- 分析任务可创建和查看
- 待复盘任务显示正确

---

## 🔧 常见问题

### 1. 数据库连接失败
- 检查 PostgreSQL 服务是否运行
- 验证数据库配置是否正确（`investment-back/.env`）
- 确保执行了 SQL 初始化脚本

### 2. 前端无法连接后端
- 确认后端服务是否在 8000 端口运行
- 检查防火墙设置
- 查看浏览器控制台的错误信息

### 3. 依赖安装失败
- **前端**：尝试删除 node_modules 重新安装
  ```bash
  cd investment-front
  rmdir /s node_modules
  npm install
  ```
- **后端**：检查 pip 版本，使用管理员权限运行

### 4. 端口冲突
- 前端默认 5173，后端默认 8000
- 如果端口被占用，修改启动脚本中的端口配置

---

## 📝 待优化事项

1. **正式认证系统**：生产环境需要实现完整的用户认证
2. **真实数据分析**：当前使用模拟数据，需要接入真实股票数据源
3. **AI 模型集成**：后端预留了 AI 接口，需要接入真实的 LLM 服务
4. **数据库优化**：添加索引和分区以提高查询效率
5. **错误处理**：增强异常处理和用户反馈

---

## 📚 相关文档

- **产品设计**：`design/ai_investment_decision_system_v_4.md`
- **UI 结构**：`structure/ai_investment_decision_system_ui_structure_design.md`
- **数据库设计**：`structure/database_design.md`
- **快速启动**：`PROJECT_README.md`

---

## 🔒 安全提示

- 开发模式下使用默认配置，生产环境请修改：
  - `SECRET_KEY` - 使用强密码
  - `DATABASE_URL` - 使用安全的连接字符串
  - `BACKEND_CORS_ORIGINS` - 限制访问来源
- 定期更新依赖包以修复安全漏洞
- 配置日志和监控系统

---

**祝您部署顺利！** 🎉
