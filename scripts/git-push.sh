#!/bin/bash
# Git 推送脚本 - 开发机使用
# 功能：推送代码并自动创建版本标签

set -e

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查是否已初始化 git
if [ ! -d ".git" ]; then
    error "未找到 Git 仓库，正在初始化..."
    git init
fi

# 添加远程仓库（如果不存在）
if ! git remote | grep -q "^origin$"; then
    info "添加远程仓库..."
    git remote add origin git@github.com:lizi-learn/battery_monitor.git 2>/dev/null || \
    git remote set-url origin git@github.com:lizi-learn/battery_monitor.git
fi

# 获取当前最新版本标签
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
info "当前版本: ${CURRENT_VERSION}"

# 解析版本号并递增
VERSION_PREFIX=$(echo "$CURRENT_VERSION" | sed 's/v//')
IFS='.' read -ra VERSION_PARTS <<< "$VERSION_PREFIX"
MAJOR=${VERSION_PARTS[0]:-1}
MINOR=${VERSION_PARTS[1]:-0}
PATCH=${VERSION_PARTS[2]:-0}

# 根据参数决定递增哪个版本号
VERSION_TYPE="${1:-patch}"  # major, minor, patch

case "$VERSION_TYPE" in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch|*)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"
info "新版本: ${NEW_VERSION}"

# 检查是否有未提交的更改
if ! git diff --quiet || ! git diff --cached --quiet; then
    # 添加所有文件
    git add .
    
    # 获取提交信息
    if [ -n "$2" ]; then
        COMMIT_MSG="$2"
    else
        COMMIT_MSG="chore: 更新代码 (${NEW_VERSION})"
    fi
    
    info "提交更改: ${COMMIT_MSG}"
    git commit -m "${COMMIT_MSG}"
else
    info "没有待提交的更改"
fi

# 设置主分支
git branch -M main 2>/dev/null || true

# 推送到远程
info "推送到远程仓库..."
git push -u origin main

# 创建并推送版本标签
info "创建版本标签: ${NEW_VERSION}"
git tag -a "${NEW_VERSION}" -m "版本 ${NEW_VERSION}

$(git log --oneline -5 | sed 's/^/  - /')"

git push origin "${NEW_VERSION}"

success "推送完成！"
success "版本: ${CURRENT_VERSION} -> ${NEW_VERSION}"
echo ""
info "部署机可以使用以下命令拉取:"
echo "  bash scripts/git-pull.sh"
echo "  或"
echo "  bash scripts/git-pull.sh ${NEW_VERSION}  # 拉取指定版本"
