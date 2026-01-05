#!/bin/bash
# Docker 快速启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "🚀 BMS 监测系统 Docker 快速启动"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: 未安装 Docker"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# 检查 docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "⚠️  警告: 未安装 docker-compose，将使用 docker run"
    USE_COMPOSE=false
else
    USE_COMPOSE=true
fi

# 查找串口设备
echo "🔍 查找串口设备..."
SERIAL_DEVICES=$(ls /dev/tty*USB* 2>/dev/null || echo "")
if [ -z "$SERIAL_DEVICES" ]; then
    echo "⚠️  警告: 未找到 USB 串口设备"
    echo "请手动指定设备路径，例如: /dev/ttyUSB0"
    read -p "输入串口设备路径 (留空使用 /dev/ttyCH341USB0): " SERIAL_DEVICE
    SERIAL_DEVICE=${SERIAL_DEVICE:-/dev/ttyCH341USB0}
else
    echo "找到以下设备:"
    echo "$SERIAL_DEVICES" | while read dev; do
        echo "  - $dev"
    done
    SERIAL_DEVICE=$(echo "$SERIAL_DEVICES" | head -1)
    echo ""
    echo "使用设备: $SERIAL_DEVICE"
    read -p "是否使用此设备? (Y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        read -p "输入设备路径: " SERIAL_DEVICE
    fi
fi

# 更新 docker-compose.yml
if [ "$USE_COMPOSE" = true ]; then
    echo ""
    echo "📝 更新 docker-compose.yml..."
    # 使用 sed 更新设备路径（简单方式）
    sed -i.bak "s|/dev/ttyCH341USB0|$SERIAL_DEVICE|g" docker-compose.yml
    
    echo "🔨 构建镜像..."
    docker-compose build
    
    echo "🚀 启动服务..."
    docker-compose up -d
    
    echo ""
    echo "✅ 启动完成！"
    echo ""
    echo "查看日志:"
    echo "  docker-compose logs -f"
    echo ""
    echo "停止服务:"
    echo "  docker-compose down"
else
    echo ""
    echo "🔨 构建镜像..."
    bash scripts/docker-build.sh
    
    echo "🚀 启动容器..."
    bash scripts/docker-run.sh "$SERIAL_DEVICE"
fi

