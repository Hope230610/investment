#!/bin/bash

# AI 投资决策系统 - 启动脚本

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== AI 投资决策系统启动脚本 ===${NC}"

# 检查 Node.js 版本
check_node_version() {
    local required_major=18
    local node_version=$(node -v 2>/dev/null || echo "0.0.0")
    local major_version=$(echo "$node_version" | cut -d'v' -f2 | cut -d'.' -f1)

    if [ "$major_version" -lt "$required_major" ]; then
        echo -e "${RED}✗ 错误：Node.js 版本过低 ($node_version)"
        echo -e "${YELLOW}请安装 Node.js $required_major 或更高版本${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ Node.js 版本检查通过 ($node_version)${NC}"
    return 0
}

# 检查 npm 版本
check_npm_version() {
    local npm_version=$(npm -v 2>/dev/null || echo "0.0.0")
    echo -e "${GREEN}✓ npm 版本检查通过 ($npm_version)${NC}"
}

# 检查 PostgreSQL 连接
check_postgres() {
    if command -v psql >/dev/null; then
        echo -e "${GREEN}✓ psql 命令可用${NC}"
        return 0
    fi

    echo -e "${YELLOW}⚠️  警告：psql 命令不可用"
    echo -e "${YELLOW}请确保 PostgreSQL 已安装并添加到系统 PATH 中${NC}"
    return 0
}

# 创建 .env 文件
create_env() {
    if [ ! -f "investment-back/.env" ]; then
        echo -e "${YELLOW}创建 investment-back/.env 文件...${NC}"
        cp investment-back/.env.example investment-back/.env
    fi

    if [ ! -f "investment-front/.env" ]; then
        echo -e "${YELLOW}创建 investment-front/.env 文件...${NC}"
        cp investment-front/.env.example investment-front/.env
    fi
}

# 安装依赖
install_dependencies() {
    echo -e "${BLUE}安装前端依赖...${NC}"
    cd investment-front
    npm install

    echo -e "${BLUE}安装后端依赖...${NC}"
    cd ../investment-back
    npm install

    cd ..
}

# 初始化数据库
init_database() {
    echo -e "${BLUE}初始化数据库...${NC}"

    local db_host="${DB_HOST:-localhost}"
    local db_port="${DB_PORT:-5432}"
    local db_name="${DB_NAME:-ai_investment_system}"
    local db_user="${DB_USER:-postgres}"
    local db_password="${DB_PASSWORD:-123456}"

    # 创建数据库（如果不存在）
    if command -v createdb >/dev/null; then
        createdb -h "$db_host" -p "$db_port" -U "$db_user" "$db_name" 2>/dev/null || true
    fi

    # 执行 SQL 脚本
    if command -v psql >/dev/null; then
        psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -f structure/migrations/001_init_schema.sql
        psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -f structure/migrations/002_init_data.sql
        psql -h "$db_host" -p "$db_port" -U "$db_user" -d "$db_name" -f structure/migrations/003_triggers.sql
    else
        echo -e "${YELLOW}⚠️  无法执行 SQL 脚本：psql 命令不可用${NC}"
        echo -e "${YELLOW}请手动执行 structure/migrations/ 目录下的 SQL 脚本${NC}"
    fi
}

# 启动后端
start_backend() {
    echo -e "${BLUE}启动后端服务...${NC}"
    cd investment-back
    npm run dev &
    local backend_pid=$!
    echo $backend_pid > .backend.pid
    cd ..

    echo -e "${GREEN}✓ 后端服务已启动 (PID: $backend_pid)${NC}"
    echo -e "${BLUE}后端地址：http://localhost:3001${NC}"
}

# 启动前端
start_frontend() {
    echo -e "${BLUE}启动前端服务...${NC}"
    cd investment-front
    npm run dev &
    local frontend_pid=$!
    echo $frontend_pid > .frontend.pid
    cd ..

    echo -e "${GREEN}✓ 前端服务已启动 (PID: $frontend_pid)${NC}"
    echo -e "${BLUE}前端地址：http://localhost:5173${NC}"
}

# 清理
cleanup() {
    echo -e "\n${BLUE}正在停止服务...${NC}"

    if [ -f "investment-back/.backend.pid" ]; then
        read -r pid < investment-back/.backend.pid
        kill "$pid" 2>/dev/null || true
        rm -f investment-back/.backend.pid
        echo -e "${GREEN}✓ 后端服务已停止${NC}"
    fi

    if [ -f "investment-front/.frontend.pid" ]; then
        read -r pid < investment-front/.frontend.pid
        kill "$pid" 2>/dev/null || true
        rm -f investment-front/.frontend.pid
        echo -e "${GREEN}✓ 前端服务已停止${NC}"
    fi
}

# 显示菜单
show_menu() {
    echo -e "\n${BLUE}请选择操作：${NC}"
    echo -e "1. ${GREEN}完整启动 (安装依赖 + 初始化数据库 + 启动前后端)${NC}"
    echo -e "2. ${GREEN}快速启动 (直接启动前后端)${NC}"
    echo -e "3. ${YELLOW}仅安装依赖${NC}"
    echo -e "4. ${YELLOW}仅初始化数据库${NC}"
    echo -e "5. ${RED}停止服务${NC}"
    echo -e "6. ${RED}退出${NC}"

    read -p "请输入选项 (1-6): " choice
}

# 主程序
main() {
    trap cleanup EXIT

    while true; do
        show_menu

        case $choice in
            1)
                echo -e "\n${BLUE}=== 完整启动 ===${NC}"
                check_node_version
                check_npm_version
                check_postgres
                create_env
                install_dependencies
                init_database
                start_backend
                sleep 3
                start_frontend
                break
                ;;
            2)
                echo -e "\n${BLUE}=== 快速启动 ===${NC}"
                check_node_version
                check_npm_version
                create_env
                start_backend
                sleep 3
                start_frontend
                break
                ;;
            3)
                echo -e "\n${BLUE}=== 安装依赖 ===${NC}"
                check_node_version
                create_env
                install_dependencies
                break
                ;;
            4)
                echo -e "\n${BLUE}=== 初始化数据库 ===${NC}"
                check_postgres
                init_database
                break
                ;;
            5)
                echo -e "\n${BLUE}=== 停止服务 ===${NC}"
                cleanup
                break
                ;;
            6)
                echo -e "\n${BLUE}=== 退出 ===${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选项，请输入 1-6${NC}"
                ;;
        esac
    done

    # 等待输入停止
    echo -e "\n${BLUE}系统已启动完成！${NC}"
    echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"

    read -r
}

main
