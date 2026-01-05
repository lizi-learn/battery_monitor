#!/bin/bash
# Git 版本查看脚本
# 功能：查看当前版本和可用版本列表

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
version() { echo -e "${CYAN}[VERSION]${NC} $1"; }

# 检查是否已初始化 git
if [ ! -d ".git" ]; then
    warning "未找到 Git 仓库"
    exit 1
fi

# 获取本地当前版本
LOCAL_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未找到版本")
if [ -f ".git_current_version" ]; then
    LOCAL_VERSION=$(cat .git_current_version)
fi

version "本地当前版本: ${LOCAL_VERSION}"

# 获取上一个版本（如果存在）
if [ -f ".git_previous_version" ]; then
    PREVIOUS_VERSION=$(cat .git_previous_version)
    version "上一个版本: ${PREVIOUS_VERSION}"
fi

# 获取远程版本信息
if git remote | grep -q "^origin$"; then
    echo ""
    info "获取远程版本信息..."
    git fetch origin --tags 2>/dev/null || {
        warning "无法连接到远程仓库"
    }
    
    REMOTE_LATEST=$(git ls-remote --tags origin 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
    if [ -n "$REMOTE_LATEST" ]; then
        version "远程最新版本: ${REMOTE_LATEST}"
        
        if [ "$LOCAL_VERSION" != "$REMOTE_LATEST" ] && [ "$LOCAL_VERSION" != "未找到版本" ]; then
            warning "本地版本落后于远程版本"
        fi
    fi
fi

# 显示所有可用版本
echo ""
info "所有可用版本:"
ALL_VERSIONS=($(git tag -l | sort -V))
if [ ${#ALL_VERSIONS[@]} -eq 0 ]; then
    warning "未找到版本标签"
else
    for ver in "${ALL_VERSIONS[@]}"; do
        if [ "$ver" = "$LOCAL_VERSION" ]; then
            echo -e "  ${GREEN}→${NC} ${ver} ${YELLOW}(当前)${NC}"
        else
            echo "    ${ver}"
        fi
    done
fi

# 显示当前commit信息
echo ""
info "当前提交信息:"
git log --oneline -1 2>/dev/null || warning "无法获取提交信息"

