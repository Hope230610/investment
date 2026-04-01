@echo off
echo 正在启动AI投资决策助手后端服务...

REM 检查Python是否可用
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未找到Python。请确保已安装Python并配置到PATH中。
    pause
    exit /b 1
)

REM 检查依赖是否已安装
pip list | findstr fastapi >nul
if %errorlevel% neq 0 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo 错误: 依赖安装失败。
        pause
        exit /b 1
    )
)

REM 启动应用
echo 启动服务...
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
