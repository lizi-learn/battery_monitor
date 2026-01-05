#!/bin/bash
# Git 推送脚本

set -e

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

# 检查是否已初始化 git
if [ ! -d ".git" ]; then
    echo "初始化 Git 仓库..."
    git init
fi

# 添加远程仓库（如果不存在）
if ! git remote | grep -q "^origin$"; then
    echo "添加远程仓库..."
    git remote add origin git@github.com:lizi-learn/battery_monitor.git 2>/dev/null || \
    git remote set-url origin git@github.com:lizi-learn/battery_monitor.git
fi

# 添加所有文件
git add .

# 提交（如果有待提交的更改）
if ! git diff --cached --quiet; then
    COMMIT_MSG="${1:-更新代码}"
    git commit -m "${COMMIT_MSG}"
else
    echo "没有待提交的更改"
fi

# 设置主分支
git branch -M main

# 推送到远程
echo "推送到远程仓库..."
git push -u origin main

echo "完成！"