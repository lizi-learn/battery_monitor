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
HAS_CHANGES=false
if ! git diff --quiet || ! git diff --cached --quiet; then
    HAS_CHANGES=true
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
    
    # 检查是否有未推送的提交
    if git rev-list HEAD ^origin/main 2>/dev/null | grep -q .; then
        HAS_CHANGES=true
        info "检测到未推送的提交，将推送这些提交"
    else
        # 没有代码变更，也没有未推送的提交
        warning "没有代码变更，也没有未推送的提交"
        echo ""
        read -p "是否仍要创建新版本标签 ${NEW_VERSION}? (y/N): " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            info "已取消，未创建新版本"
            exit 0
        fi
        info "将创建新版本标签（无代码变更）"
    fi
fi

# 设置主分支
git branch -M main 2>/dev/null || true

# 推送到远程（如果有变更或未推送的提交）
if [ "$HAS_CHANGES" = true ]; then
    info "推送到远程仓库..."
    git push -u origin main
fi

# 检查版本标签是否已存在
if git rev-parse "${NEW_VERSION}" >/dev/null 2>&1; then
    warning "版本标签 ${NEW_VERSION} 已存在"
    read -p "是否覆盖现有标签? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "删除本地标签..."
        git tag -d "${NEW_VERSION}" 2>/dev/null || true
        info "删除远程标签..."
        git push origin ":refs/tags/${NEW_VERSION}" 2>/dev/null || true
    else
        error "版本标签已存在，操作已取消"
        exit 1
    fi
fi

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
