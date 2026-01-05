#!/bin/bash
# 版本服务脚本 - 开发机使用（可选）
# 功能：启动一个简单的HTTP服务，提供版本信息（用于部署机轮询）
# 注意：如果使用Git仓库直接提供版本信息，此脚本可选

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

PORT="${1:-8080}"

info() { echo -e "\033[0;34m[INFO]\033[0m $1"; }

if ! command -v python3 >/dev/null 2>&1; then
    echo "错误: 需要 python3"
    exit 1
fi

info "启动版本信息服务在端口 ${PORT}..."
info "访问 http://localhost:${PORT}/version 查看版本信息"
info "按 Ctrl+C 停止"

# 使用Python内置HTTP服务器
python3 -m http.server "$PORT" --directory "${PROJECT_ROOT}"

