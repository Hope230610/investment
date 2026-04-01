#!/bin/bash

# AI投资决策助手部署脚本
# 该脚本用于快速部署应用到生产环境

# 脚本颜色常量
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印信息函数
print_info() {
    echo -e "${GREEN}INFO: ${1}${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: ${1}${NC}"
}

print_error() {
    echo -e "${RED}ERROR: ${1}${NC}"
}

# 检查依赖函数
check_dependencies() {
    print_info "检查依赖..."

    local all_ok=true

    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        all_ok=false
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装"
        all_ok=false
    fi

    if ! command -v git &> /dev/null; then
        print_error "Git未安装"
        all_ok=false
    fi

    if ! command -v curl &> /dev/null; then
        print_error "Curl未安装"
        all_ok=false
    fi

    if ! $all_ok; then
        print_error "请先安装所需依赖"
        exit 1
    fi

    print_info "所有依赖检查通过"
}

# 检查端口是否被占用
check_ports() {
    print_info "检查端口占用..."

    local ports=("8000" "5432" "8080")

    for port in "${ports[@]}"; do
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            print_warning "端口 $port 被占用"
        fi
    done
}

# 创建部署目录
create_deployment_dir() {
    local target_dir="${1}"

    if [ -d "$target_dir" ]; then
        print_warning "部署目录 $target_dir 已存在"
        read -p "是否要删除现有目录并重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$target_dir"
        else
            print_warning "使用现有目录"
            return
        fi
    fi

    mkdir -p "$target_dir"
    print_info "创建部署目录 $target_dir"
}

# 复制配置文件
copy_config_files() {
    local target_dir="${1}"
    local source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # 复制项目文件
    print_info "复制项目文件到 $target_dir..."

    cp -r "${source_dir}"/* "${target_dir}/"
    cp -r "${source_dir}"/.* "${target_dir}/" 2>/dev/null || true

    # 复制环境变量文件
    if [ ! -f "${target_dir}/.env" ]; then
        if [ -f "${target_dir}/.env.example" ]; then
            cp "${target_dir}/.env.example" "${target_dir}/.env"
            print_info "已创建 .env 文件，请根据需要修改配置"
        else
            print_warning "未找到环境变量配置文件"
        fi
    else
        print_info "使用现有的 .env 文件"
    fi
}

# 构建和启动服务
build_and_start() {
    local target_dir="${1}"
    local compose_file="${target_dir}/docker-compose.yml"

    print_info "开始构建和启动服务..."

    cd "$target_dir" || exit 1

    if [ ! -f "$compose_file" ]; then
        print_error "未找到 docker-compose.yml 文件"
        return 1
    fi

    # 构建并启动
    if docker-compose up -d --build; then
        print_info "服务启动成功"

        # 检查数据库是否准备好
        print_info "检查数据库连接..."
        local db_attempts=0
        local db_max_attempts=30

        while [ $db_attempts -lt $db_max_attempts ]; do
            if curl -s "http://localhost:8000/health" > /dev/null; then
                print_info "数据库连接成功"
                break
            fi
            db_attempts=$((db_attempts + 1))
            print_warning "数据库连接检查中... $db_attempts/$db_max_attempts"
            sleep 2
        done

        if [ $db_attempts -ge $db_max_attempts ]; then
            print_error "数据库连接超时"
            return 1
        fi
    else
        print_error "服务启动失败"
        return 1
    fi
}

# 健康检查
check_health() {
    local target_dir="${1}"
    local compose_file="${target_dir}/docker-compose.yml"

    print_info "进行健康检查..."

    cd "$target_dir" || exit 1

    if [ ! -f "$compose_file" ]; then
        print_error "未找到 docker-compose.yml 文件"
        return 1
    fi

    # 检查服务是否正常运行
    if docker-compose ps | grep -q "Up"; then
        print_info "服务运行状态良好"
    else
        print_error "服务运行状态异常"
        return 1
    fi

    # 检查健康接口
    if curl -s "http://localhost:8000/health" > /dev/null; then
        print_info "健康检查通过"
    else
        print_error "健康检查失败"
        return 1
    fi
}

# 显示部署信息
show_deployment_info() {
    local target_dir="${1}"

    print_info "部署成功！"
    echo
    print_info "访问地址:"
    echo -e "${GREEN}主应用: http://localhost:8000${NC}"
    echo -e "${GREEN}API文档: http://localhost:8000/api/v1/docs${NC}"
    echo -e "${GREEN}数据库管理: http://localhost:8080${NC}"
    echo
    print_info "可用命令:"
    echo -e "  查看日志: ${YELLOW}docker-compose logs -f${NC}"
    echo -e "  停止服务: ${YELLOW}docker-compose down${NC}"
    echo -e "  重启服务: ${YELLOW}docker-compose restart${NC}"
    echo
    print_info "数据库信息:"
    echo -e "  默认数据库: $(grep 'DB_NAME' "${target_dir}/.env" | cut -d'=' -f2)"
    echo -e "  用户名: $(grep 'DB_USER' "${target_dir}/.env" | cut -d'=' -f2)"
    echo -e "  密码: $(grep 'DB_PASSWORD' "${target_dir}/.env" | cut -d'=' -f2)"
}

# 显示帮助信息
show_help() {
    cat << EOF
部署脚本使用说明:

  $0 [OPTIONS] <部署目录>

  选项:
    -h, --help    显示此帮助信息
    -c, --check   只检查依赖和环境，不执行部署

  示例:
    $0 --check                           # 只检查依赖和环境
    $0 /opt/investment-app              # 部署到 /opt/investment-app
    $0 -v /home/user/deploy/investment  # 详细模式部署

EOF
}

# 解析命令行参数
parse_args() {
    local OPTIND=1

    while getopts ":hcv" opt; do
        case $opt in
            h)
                show_help
                exit 0
                ;;
            c)
                check_mode=true
                ;;
            v)
                verbose_mode=true
                ;;
            \?)
                echo "无效的选项: -$OPTARG" >&2
                show_help
                exit 1
                ;;
        esac
    done

    shift $((OPTIND - 1))

    if [ "$check_mode" = true ]; then
        check_dependencies
        check_ports
        print_info "检查完成"
        exit 0
    fi

    if [ $# -eq 0 ]; then
        target_dir="/opt/investment-app"
        print_info "未指定部署目录，使用默认目录 $target_dir"
    else
        target_dir="$1"
        print_info "部署到 $target_dir"
    fi

    return 0
}

# 主函数
main() {
    local target_dir

    if ! parse_args "$@"; then
        show_help
        exit 1
    fi

    check_dependencies
    check_ports
    create_deployment_dir "$target_dir"
    copy_config_files "$target_dir"

    if build_and_start "$target_dir"; then
        if check_health "$target_dir"; then
            show_deployment_info "$target_dir"
        fi
    else
        print_error "部署失败"
        exit 1
    fi
}

# 程序入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
