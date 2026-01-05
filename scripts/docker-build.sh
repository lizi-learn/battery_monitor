#!/bin/bash
# Docker 构建脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "🔨 构建 BMS 监测系统 Docker 镜像..."

# 构建镜像
docker build -t bms-monitor:latest .

echo "✅ 构建完成！"
echo ""
echo "使用方法:"
echo "  1. 使用 docker-compose (推荐):"
echo "     docker-compose up -d"
echo ""
echo "  2. 直接使用 docker run:"
echo "     docker run -d --name bms-monitor \\"
echo "       --device=/dev/ttyCH341USB0:/dev/ttyCH341USB0 \\"
echo "       -v \$(pwd)/config:/app/config:ro \\"
echo "       -v \$(pwd)/logs:/app/logs \\"
echo "       bms-monitor:latest"

