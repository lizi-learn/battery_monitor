#!/bin/bash
# Git 拉取脚本 - 部署机使用
# 功能：拉取代码并显示版本信息，支持版本回退

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
    error "未找到 Git 仓库，正在初始化..."
    git init
    git branch -M main
fi

# 添加远程仓库（如果不存在）
if ! git remote | grep -q "^origin$"; then
    info "添加远程仓库..."
    git remote add origin git@github.com:lizi-learn/battery_monitor.git
fi

# 获取当前版本（本地）
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未找到版本")
if [ "$CURRENT_VERSION" = "未找到版本" ]; then
    warning "本地未找到版本标签，可能是首次拉取"
    CURRENT_VERSION="无"
fi

version "当前本地版本: ${CURRENT_VERSION}"

# 获取远程最新版本
info "获取远程版本信息..."
git fetch origin --tags 2>/dev/null || {
    error "无法连接到远程仓库，请检查网络和SSH配置"
    exit 1
}

# 获取远程最新版本标签
REMOTE_LATEST=$(git ls-remote --tags origin | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)

if [ -z "$REMOTE_LATEST" ]; then
    error "远程仓库未找到版本标签"
    exit 1
fi

version "远程最新版本: ${REMOTE_LATEST}"

# 如果指定了版本，使用指定版本；否则使用最新版本
TARGET_VERSION="${1:-${REMOTE_LATEST}}"

# 检查版本是否存在
if ! git ls-remote --tags origin | grep -q "refs/tags/${TARGET_VERSION}$"; then
    error "版本 ${TARGET_VERSION} 不存在"
    info "可用版本列表:"
    git ls-remote --tags origin | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V
    exit 1
fi

# 显示版本变更信息
echo ""
info "版本变更信息:"
if [ "$CURRENT_VERSION" != "无" ] && [ "$CURRENT_VERSION" != "$TARGET_VERSION" ]; then
    echo "  ${CURRENT_VERSION} -> ${TARGET_VERSION}"
    
    # 获取变更日志
    if [ "$CURRENT_VERSION" != "无" ]; then
        info "变更内容:"
        git log --oneline "${CURRENT_VERSION}..${TARGET_VERSION}" 2>/dev/null | sed 's/^/  - /' || echo "  (无法获取变更日志)"
    fi
elif [ "$CURRENT_VERSION" = "$TARGET_VERSION" ]; then
    success "已是最新版本，无需更新"
    exit 0
fi

echo ""
read -p "是否继续拉取版本 ${TARGET_VERSION}? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    info "已取消"
    exit 0
fi

# 保存当前版本到文件（用于回退）
if [ "$CURRENT_VERSION" != "无" ]; then
    echo "$CURRENT_VERSION" > .git_previous_version
    info "已保存当前版本 ${CURRENT_VERSION} 到 .git_previous_version（用于回退）"
fi

# 拉取代码
info "拉取代码..."
git fetch origin main

# 切换到指定版本
info "切换到版本: ${TARGET_VERSION}"
git checkout "${TARGET_VERSION}" 2>/dev/null || {
    # 如果checkout失败，可能是标签指向的commit不在当前分支
    # 先拉取所有标签，然后checkout
    git fetch origin --tags
    git checkout -b "version-${TARGET_VERSION}" "${TARGET_VERSION}" 2>/dev/null || {
        # 如果还是失败，直接reset到标签指向的commit
        COMMIT_HASH=$(git rev-list -n 1 "${TARGET_VERSION}")
        git checkout main
        git reset --hard "${COMMIT_HASH}"
    }
}

# 保存新版本到文件
echo "$TARGET_VERSION" > .git_current_version

success "拉取完成！"
echo ""
version "版本信息:"
version "  拉取前: ${CURRENT_VERSION}"
version "  拉取后: ${TARGET_VERSION}"
echo ""
info "如需回退到上一个版本，运行:"
echo "  bash scripts/git-rollback.sh"

