@echo off
REM AI 投资决策系统 - Python 版本启动脚本
chcp 65001 >nul
title AI 投资决策系统

echo ====================================
echo AI 投资决策系统 - Python 版本
echo ====================================
echo.

:MENU
echo.
echo 请选择操作:
echo 1. 完整启动 (安装依赖 + 初始化数据库 + 启动前后端)
echo 2. 快速启动 (直接启动前后端)
echo 3. 仅安装依赖
echo 4. 仅初始化数据库
echo 5. 停止服务
echo 6. 退出
echo.

set /p choice="请输入选项 (1-6): "

if "%choice%"=="1" goto FULL_START
if "%choice%"=="2" goto QUICK_START
if "%choice%"=="3" goto INSTALL_DEPS
if "%choice%"=="4" goto INIT_DB
if "%choice%"=="5" goto STOP
if "%choice%"=="6" goto EXIT
echo 无效选项，请重新选择
goto MENU

:FULL_START
echo.
echo [1/6] 检查 Node.js 版本...
node -v >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Node.js，请先安装 Node.js 18+
    goto MENU
)
for /f "tokens=2 delims=v." %%a in ('node -v') do set major=%%a
if %major% LSS 18 (
    echo 错误: Node.js 版本过低，请安装 18+
    goto MENU
)
echo Node.js 版本检查通过
node -v

echo.
echo [2/6] 检查 Python 版本...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.9+
    goto MENU
)
for /f "tokens=2" %%a in ('python --version') do set pyversion=%%a
for /f "tokens=1 delims=." %%a in ("%pyversion%") do set major=%%a
if %major% LSS 3 (
    echo 错误: Python 版本过低，请安装 3.9+
    goto MENU
)
echo Python 版本检查通过
python --version

echo.
echo [3/6] 创建环境变量文件...
if not exist "investment-back\.env" (
    copy "investment-back\.env.example" "investment-back\.env"
    echo 创建 investment-back\.env
)
if not exist "investment-front\.env" (
    copy "investment-front\.env.example" "investment-front\.env"
    echo 创建 investment-front\.env
)

echo.
echo [4/6] 安装依赖...
cd investment-front
call npm install
if errorlevel 1 (
    echo 错误: 前端依赖安装失败
    cd ..
    goto MENU
)
cd ..

cd investment-back
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 后端依赖安装失败
    cd ..
    goto MENU
)
cd ..

echo.
echo [5/6] 初始化数据库...
echo 请手动执行以下 SQL 脚本:
echo   1. structure/migrations/001_init_schema.sql
echo   2. structure/migrations/002_init_data.sql
echo   3. structure/migrations/003_triggers.sql
echo.
echo 按任意键继续...
pause >nul

echo.
echo [6/6] 启动服务...
echo 启动后端 (端口 8000)...
start "AI Backend" cmd /k "cd investment-back && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo 启动前端 (端口 5173)...
start "AI Frontend" cmd /k "cd investment-front && npm run dev"

echo.
echo ====================================
echo 启动完成!
echo 后端: http://localhost:8000
echo 后端文档: http://localhost:8000/api/v1/docs
echo 前端: http://localhost:5173
echo.
echo 关闭此窗口会保持后端和前端运行
echo 或在后端/前端窗口按 Ctrl+C 停止
echo ====================================
goto EXIT

:QUICK_START
echo.
echo 快速启动服务...

if not exist "investment-back\.env" (
    copy "investment-back\.env.example" "investment-back\.env"
)
if not exist "investment-front\.env" (
    copy "investment-front\.env.example" "investment-front\.env"
)

echo 启动后端 (端口 8000)...
start "AI Backend" cmd /k "cd investment-back && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 >nul

echo 启动前端 (端口 5173)...
start "AI Frontend" cmd /k "cd investment-front && npm run dev"

echo.
echo ====================================
echo 启动完成!
echo 后端: http://localhost:8000
echo 后端文档: http://localhost:8000/api/v1/docs
echo 前端: http://localhost:5173
echo ====================================
goto EXIT

:INSTALL_DEPS
echo.
echo 安装前端依赖...
cd investment-front
call npm install
cd ..

echo.
echo 安装后端依赖...
cd investment-back
pip install -r requirements.txt
cd ..

echo.
echo 依赖安装完成!
goto MENU

:INIT_DB
echo.
echo ====================================
echo 数据库初始化
echo ====================================
echo.
echo 请使用 pgAdmin 或 psql 执行以下 SQL 脚本:
echo.
echo 1. structure/migrations/001_init_schema.sql
echo    - 创建所有表结构
echo.
echo 2. structure/migrations/002_init_data.sql
echo    - 插入示例数据 (示例股票、系统配置等)
echo.
echo 3. structure/migrations/003_triggers.sql
echo    - 创建触发器和视图
echo.
echo 数据库配置:
echo   DB_HOST: localhost
echo   DB_PORT: 5432
echo   DB_NAME: investment_db
echo   DB_USER: postgres
echo   DB_PASSWORD: 123456
echo.
echo 请先创建数据库，然后执行上述脚本
echo.
pause
goto MENU

:STOP
echo.
echo 停止服务...
echo.
echo 请在后端/前端窗口按 Ctrl+C 停止服务
echo.
pause
goto MENU

:EXIT
echo.
echo 再见!
timeout /t 2 >nul
