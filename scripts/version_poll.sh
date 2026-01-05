#!/bin/bash
# 版本轮询脚本 - 部署机使用
# 功能：定期检查远程版本，如果检测到新版本且配置允许，触发watchtower更新

set -e

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }
version() { echo -e "${CYAN}[VERSION]${NC} $1"; }

# 检查是否在Docker环境中
IN_DOCKER=false
if [ -f /.dockerenv ] || grep -qa docker /proc/1/cgroup 2>/dev/null; then
    IN_DOCKER=true
fi

# 检查版本更新
check_update() {
    info "检查版本更新..."
    
    # 使用Python脚本检查版本
    CHECK_RESULT=$(python3 scripts/version_check.py 2>/dev/null)
    
    if [ $? -ne 0 ] || [ -z "$CHECK_RESULT" ]; then
        error "版本检查失败"
        return 1
    fi
    
    # 解析JSON结果（使用python解析）
    NEED_UPDATE=$(echo "$CHECK_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('need_update', False))" 2>/dev/null)
    AUTO_UPDATE_ENABLED=$(echo "$CHECK_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('auto_update_enabled', False))" 2>/dev/null)
    LOCAL_VERSION=$(echo "$CHECK_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('local_version', 'unknown'))" 2>/dev/null)
    REMOTE_VERSION=$(echo "$CHECK_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('remote_version', 'unknown'))" 2>/dev/null)
    FLAGS_JSON=$(echo "$CHECK_RESULT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('flags', {})))" 2>/dev/null)
    
    version "本地版本: ${LOCAL_VERSION}"
    version "远程版本: ${REMOTE_VERSION}"
    
    if [ "$NEED_UPDATE" = "True" ]; then
        info "检测到新版本: ${LOCAL_VERSION} -> ${REMOTE_VERSION}"
        
        if [ "$AUTO_UPDATE_ENABLED" = "True" ]; then
            info "自动更新已启用，将触发更新..."
            
            # 显示标志信息
            if [ -n "$FLAGS_JSON" ] && [ "$FLAGS_JSON" != "{}" ]; then
                info "版本标志: ${FLAGS_JSON}"
            fi
            
            # 触发watchtower更新
            trigger_watchtower_update
            
            return 0
        else
            warning "检测到新版本，但自动更新未启用（开发机配置: auto_update_enabled=false）"
            warning "如需手动更新，运行: bash scripts/git-pull.sh"
            return 1
        fi
    else
        info "当前已是最新版本"
        return 0
    fi
}

# 触发watchtower更新
trigger_watchtower_update() {
    info "触发watchtower更新..."
    
    if [ "$IN_DOCKER" = "true" ]; then
        # 在Docker容器中，通过发送信号给watchtower或重启容器
        warning "当前在Docker容器中运行"
        warning "请确保watchtower正在运行，它将自动检测新版本并更新容器"
        
        # 如果是通过docker-compose运行，可以触发重新拉取
        if command -v docker-compose >/dev/null 2>&1; then
            info "使用docker-compose重新拉取并启动..."
            docker-compose pull
            docker-compose up -d
            success "容器已更新"
        fi
    else
        # 在宿主机上，触发watchtower或重新构建/拉取
        if command -v docker-compose >/dev/null 2>&1; then
            info "使用docker-compose重新拉取并启动..."
            cd "$PROJECT_ROOT"
            docker-compose pull
            docker-compose up -d --build
            success "容器已更新"
        elif command -v docker >/dev/null 2>&1; then
            # 如果有watchtower容器，可以通过发送信号触发更新
            if docker ps --format '{{.Names}}' | grep -q watchtower; then
                info "发送信号给watchtower容器..."
                docker kill -s SIGUSR2 $(docker ps --format '{{.Names}}' | grep watchtower | head -1)
                success "已触发watchtower更新"
            else
                warning "未找到watchtower容器，请手动更新"
            fi
        else
            warning "未找到docker或docker-compose，无法自动更新容器"
            warning "请手动运行: bash scripts/git-pull.sh"
        fi
    fi
}

# 单次检查模式
if [ "${1}" = "--once" ]; then
    check_update
    exit $?
fi

# 轮询模式
info "启动版本轮询服务..."
info "按 Ctrl+C 停止"

# 读取配置获取轮询间隔
CHECK_INTERVAL=300  # 默认5分钟
if [ -f "config/config.yaml" ]; then
    INTERVAL_FROM_CONFIG=$(python3 -c "import yaml; f=open('config/config.yaml'); c=yaml.safe_load(f); print(c.get('version', {}).get('check_interval', 300))" 2>/dev/null)
    if [ -n "$INTERVAL_FROM_CONFIG" ] && [ "$INTERVAL_FROM_CONFIG" -gt 0 ]; then
        CHECK_INTERVAL=$INTERVAL_FROM_CONFIG
    fi
fi

info "轮询间隔: ${CHECK_INTERVAL} 秒"

# 无限循环检查
while true; do
    check_update
    sleep "$CHECK_INTERVAL"
done

