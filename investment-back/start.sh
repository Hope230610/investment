#!/bin/bash

echo "正在启动AI投资决策助手后端服务..."

# 检查Python是否可用
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo "错误: 未找到Python。请确保已安装Python并配置到PATH中。"
        exit 1
    else
        PYTHON_CMD=python
    fi
else
    PYTHON_CMD=python3
fi

# 检查依赖是否已安装
if ! $PYTHON_CMD -c "import fastapi" 2>/dev/null; then
    echo "正在安装依赖..."
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败。"
        exit 1
    fi
fi

# 启动应用
echo "启动服务..."
$PYTHON_CMD -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
