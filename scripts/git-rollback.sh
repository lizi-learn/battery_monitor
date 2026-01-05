#!/bin/bash
# Git 回退脚本 - 部署机使用
# 功能：快速回退到上一个版本

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

# 检查是否已初始化 git
if [ ! -d ".git" ]; then
    error "未找到 Git 仓库"
    exit 1
fi

# 获取当前版本
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未找到版本")
if [ -f ".git_current_version" ]; then
    CURRENT_VERSION=$(cat .git_current_version)
fi

version "当前版本: ${CURRENT_VERSION}"

# 获取上一个版本
PREVIOUS_VERSION=""
if [ -f ".git_previous_version" ]; then
    PREVIOUS_VERSION=$(cat .git_previous_version)
    version "上一个版本: ${PREVIOUS_VERSION}"
elif [ "$CURRENT_VERSION" != "未找到版本" ]; then
    # 尝试从git历史中获取上一个版本
    ALL_VERSIONS=($(git tag -l | sort -V))
    CURRENT_INDEX=-1
    for i in "${!ALL_VERSIONS[@]}"; do
        if [ "${ALL_VERSIONS[$i]}" = "$CURRENT_VERSION" ]; then
            CURRENT_INDEX=$i
            break
        fi
    done
    
    if [ $CURRENT_INDEX -gt 0 ]; then
        PREVIOUS_VERSION="${ALL_VERSIONS[$((CURRENT_INDEX - 1))]}"
        version "上一个版本: ${PREVIOUS_VERSION}"
    fi
fi

if [ -z "$PREVIOUS_VERSION" ]; then
    error "无法找到上一个版本"
    info "可用版本列表:"
    git tag -l | sort -V
    exit 1
fi

# 显示版本信息
echo ""
info "版本回退信息:"
echo "  当前版本: ${CURRENT_VERSION}"
echo "  回退到: ${PREVIOUS_VERSION}"
echo ""

read -p "确认回退到版本 ${PREVIOUS_VERSION}? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "已取消"
    exit 0
fi

# 切换到上一个版本
info "切换到版本: ${PREVIOUS_VERSION}"
git fetch origin --tags 2>/dev/null || true

# 尝试checkout到指定版本
if git rev-parse --verify "${PREVIOUS_VERSION}" >/dev/null 2>&1; then
    git checkout "${PREVIOUS_VERSION}" 2>/dev/null || {
        COMMIT_HASH=$(git rev-list -n 1 "${PREVIOUS_VERSION}")
        git checkout main 2>/dev/null || git checkout -b main
        git reset --hard "${COMMIT_HASH}"
    }
else
    error "版本 ${PREVIOUS_VERSION} 不存在"
    exit 1
fi

# 更新版本文件
echo "$PREVIOUS_VERSION" > .git_current_version
if [ -f ".git_previous_version" ]; then
    # 保存当前版本作为新的previous
    echo "$CURRENT_VERSION" > .git_previous_version
fi

success "回退完成！"
echo ""
version "版本信息:"
version "  回退前: ${CURRENT_VERSION}"
version "  回退后: ${PREVIOUS_VERSION}"

