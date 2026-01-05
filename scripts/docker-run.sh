#!/bin/bash
# Docker 运行脚本 - 直接使用 docker run

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

# 默认串口设备
SERIAL_DEVICE="${1:-/dev/ttyCH341USB0}"

# 检查设备是否存在
if [ ! -e "$SERIAL_DEVICE" ]; then
    echo "⚠️  警告: 串口设备 $SERIAL_DEVICE 不存在"
    echo "可用设备:"
    ls -la /dev/tty*USB* 2>/dev/null || echo "  未找到 USB 串口设备"
    echo ""
    read -p "是否继续? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 检查镜像是否存在
if ! docker images | grep -q "bms-monitor.*latest"; then
    echo "📦 镜像不存在，正在构建..."
    bash scripts/docker-build.sh
fi

# 停止并删除旧容器（如果存在）
if docker ps -a | grep -q "bms-monitor"; then
    echo "🛑 停止旧容器..."
    docker stop bms-monitor 2>/dev/null || true
    docker rm bms-monitor 2>/dev/null || true
fi

# 运行容器
echo "🚀 启动 BMS 监测容器..."
echo "   串口设备: $SERIAL_DEVICE"

docker run -d \
    --name bms-monitor \
    --restart unless-stopped \
    --device="$SERIAL_DEVICE:$SERIAL_DEVICE" \
    -v "$(pwd)/config:/app/config:ro" \
    -v "$(pwd)/logs:/app/logs" \
    -e TZ=Asia/Shanghai \
    bms-monitor:latest

echo "✅ 容器已启动！"
echo ""
echo "查看日志:"
echo "  docker logs -f bms-monitor"
echo ""
echo "查看容器状态:"
echo "  docker ps | grep bms-monitor"
echo ""
echo "停止容器:"
echo "  docker stop bms-monitor"
echo ""
echo "删除容器:"
echo "  docker rm bms-monitor"

