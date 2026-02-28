#!/bin/bash

ADDR=0x0B
BAUD=9600

echo "🔍 Scanning BMS Modbus ports..."

for dev in /dev/ttyUSB*; do
  [ -e "$dev" ] || continue

  echo ""
  echo "=== Testing $dev ==="

  # 串口初始化
  stty -F "$dev" raw speed $BAUD cs8 -cstopb -parenb -ixon -ixoff

  # 构造 Modbus 请求：0B 03 08 00 00 01 86 C0
  printf "\x0B\x03\x08\x00\x00\x01\x86\xC0" > "$dev"

  # 读取响应（7 字节）
  timeout 1 head -c 7 < "$dev" | xxd
done
