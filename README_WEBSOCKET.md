# BMS 电池监测 WebSocket 上报说明

## 修改内容

`battery.py` 已添加 WebSocket 数据上报功能，可以将实时读取的 BMS 数据通过 WebSocket 上报到云端服务器。

## 配置

### WebSocket 地址
- 默认地址：`ws://43.143.74.209:3000/ws`
- 可通过环境变量 `BMS_WS_URL` 覆盖：
  ```bash
  export BMS_WS_URL="ws://your-server:3000/ws"
  ```

### 设备 UUID
- 默认 UUID：`c1011`
- 可通过环境变量 `BMS_WS_UUID` 覆盖：
  ```bash
  export BMS_WS_UUID="your-device-id"
  ```

## 依赖安装

需要安装 `websockets` 库：

```bash
pip install websockets
```

或者使用 requirements.txt（如果存在）：

```bash
pip install -r requirements.txt
```

## 数据格式

上报的数据格式与 `websocket_client_1.py` 保持一致：

```json
{
  "uuid": "c1011",
  "type": "telemetry",
  "kind": "temperature",
  "value": 30.5,           // 最高温度（℃）
  "current": 12.63,        // 电池电流（A）
  "batteryPercent": 51,    // 剩余电量（%）
  "batteryMaxTemp": 30.5,  // 电池最高温度（℃）
  "batteryVoltage": 301.5, // 电池电压（V）
  "seq": 1,                // 序列号
  "message": "设备c1011温度=30.5℃, 电流=12.63A, 电量=51%, 最高温度=30.5℃, 电压=301.5V (第 1 次上报)"
}
```

## 运行

直接运行脚本：

```bash
python battery.py
```

程序会：
1. 通过 Modbus 从 BMS 读取数据
2. 在控制台显示数据
3. 写入本地日志文件 `battrey.txt`
4. 通过 HTTP 上报（如果配置了 `BMS_HTTP_URL`）
5. **通过 WebSocket 上报到云端服务器**

## 功能说明

- **自动重连**：WebSocket 连接断开后会自动重连
- **异步处理**：WebSocket 通信在后台异步处理，不影响主循环
- **保留原有功能**：HTTP 上报、日志记录等功能均保留
- **上报频率**：每 5 秒上报一次（与 BMS 读取频率同步）

## 注意事项

1. 确保云端服务器 `43.143.74.209:3000` 的 WebSocket 服务正常运行
2. 如果网络不通，程序会打印警告信息但不会中断运行
3. 可以通过查看控制台输出来确认 WebSocket 连接状态

