#!/usr/bin/env bash
set -euo pipefail

# 用法:
#   bash deploy.sh --install    安装并启动服务
#   bash deploy.sh --uninstall  停止并卸载服务（保留程序目录）

# ========= 可根据需要修改的参数 =========
APP_USER="${APP_USER:-pc}"
APP_DIR="${APP_DIR:-/home/${APP_USER}/battery_test}"
SERVICE_NAME="${SERVICE_NAME:-battrey}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"  # 如果别的设备是 /bin/python3，就改这里
# =====================================

ACTION="${1:-}"

install_service() {
  # 当前脚本所在目录，认为 battery.py 和 deploy.sh 在同一目录
  SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

  echo "部署用户: ${APP_USER}"
  echo "应用目录: ${APP_DIR}"
  echo "服务名称: ${SERVICE_NAME}"
  echo "Python  : ${PYTHON_BIN}"
  echo "源码目录: ${SRC_DIR}"

  # 1. 拷贝程序到目标目录
  sudo mkdir -p "${APP_DIR}"
  if [[ "${SRC_DIR}" != "${APP_DIR}" ]]; then
    sudo cp "${SRC_DIR}/battery.py" "${APP_DIR}/"
  else
    echo "battery.py 已在目标目录，无需复制。"
  fi

  # 2. 修改目录权限，保证服务以 APP_USER 身份可访问
  sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"

  # 3. 创建 systemd 服务文件
  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

  sudo bash -c "cat > '${SERVICE_FILE}'" <<EOF
[Unit]
Description=BMS 电池安全监测服务
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_BIN} ${APP_DIR}/battery.py
Restart=always
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=10

[Install]
WantedBy=multi-user.target
EOF

  echo "已写入 systemd 服务: ${SERVICE_FILE}"

  # 4. 重新加载 systemd，启用并立即启动服务
  sudo systemctl daemon-reload
  sudo systemctl enable --now "${SERVICE_NAME}.service"

  echo "部署完成。"
  echo "查看服务状态: sudo systemctl status ${SERVICE_NAME}.service"
  echo "查看程序日志: tail -f ${APP_DIR}/battrey.txt"
}

uninstall_service() {
  echo "卸载服务: ${SERVICE_NAME}"

  # 停止并禁用服务（如不存在则忽略错误）
  sudo systemctl disable --now "${SERVICE_NAME}.service" 2>/dev/null || true

  # 删除 systemd 服务文件
  SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
  sudo rm -f "${SERVICE_FILE}"

  # 重新加载 systemd
  sudo systemctl daemon-reload

  echo "已卸载服务 ${SERVICE_NAME}。应用目录 ${APP_DIR} 保留，如需删除可手动 rm -rf。"
}

case "${ACTION}" in
  --install)
    install_service
    ;;
  --uninstall)
    uninstall_service
    ;;
  *)
    echo "用法: $0 --install | --uninstall"
    exit 1
    ;;
esac