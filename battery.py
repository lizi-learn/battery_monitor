from __future__ import annotations

import os
import serial
import struct
import time
import json
import asyncio
import websockets
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK


# 串口 & Modbus 基本配置，可按需修改
PORT = "/dev/ttyCH341USB1"
BAUDRATE = 9600
ADDR = 0x0B
TIMEOUT = 0.5

# 日志文件放在脚本同目录（例如 /home/pc/battery_test/battrey.txt）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(BASE_DIR, "battrey.txt")
MAX_LOG_SIZE = 200 * 1024  # 日志最大约 200KB

# 云端 WebSocket 地址（可通过环境变量 BMS_WS_URL 覆盖）
CLOUD_WS_URL = os.environ.get("BMS_WS_URL", "ws://43.143.74.209:3000/ws")
WS_UUID = os.environ.get("BMS_WS_UUID", "c1012")
_ws_client = None
_ws_connected = False
_ws_warned = False


def crc16_modbus(data: bytes) -> int:
    """CRC-16/MODBUS 计算"""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def modbus_read_regs(ser, start_addr: int, count: int):
    """
    连续读取多个保持寄存器（功能码 0x03）
    返回: [reg0, reg1, ...] 或 None（失败）
    """
    frame = struct.pack(">B B H H", ADDR, 0x03, start_addr, count)
    crc = crc16_modbus(frame)
    frame += struct.pack("<H", crc)

    # 清空缓冲，避免旧数据干扰
    ser.reset_input_buffer()
    ser.write(frame)

    resp = ser.read(5 + count * 2)
    if len(resp) < 5:
        return None

    # 地址 & 功能码检查
    if resp[0] != ADDR or resp[1] != 0x03:
        return None

    # CRC 校验
    crc_recv = struct.unpack("<H", resp[-2:])[0]
    if crc_recv != crc16_modbus(resp[:-2]):
        return None

    data = resp[3:-2]
    regs = [
        struct.unpack(">H", data[i:i + 2])[0]
        for i in range(0, len(data), 2)
    ]
    return regs


def u32(lo: int, hi: int) -> int:
    """将两个 16bit（L 寄存器、H 寄存器）合成为无符号 32bit"""
    return (hi << 16) | lo


def s32(lo: int, hi: int) -> int:
    """将两个 16bit 合成为有符号 32bit（用于电池电流 Current）"""
    val = (hi << 16) | lo
    if val & 0x80000000:
        val -= 0x100000000
    return val


def check_alarms(pack_v: float, current_a: float, soc: int, tmax_c: float):
    """
    简单安全阈值判断，返回告警列表（字符串）。
    阈值只是示例，可按需要自行调整。
    """
    alarms = []

    # 电压阈值（根据实际电池规格调整）
    if pack_v > 58.4:
        alarms.append("PACK 电压过高")
    if pack_v < 40.0:
        alarms.append("PACK 电压过低")

    # 温度阈值（°C）
    if tmax_c > 60.0:
        alarms.append("最高温度过高")
    if tmax_c < 0.0:
        alarms.append("环境过低温")

    # SOC 极端值提示（非保护，只是提示）
    if soc >= 100:
        alarms.append("电量已满")
    if soc <= 5:
        alarms.append("电量过低")

    return alarms


# ===== 通信协议中的告警/安全位定义（简化版） =====

BATTERY_ALARM_BITS = {
    0: "CUV 单体电池欠压",
    1: "OCD 放电过流",
    2: "SCD 电池短路",
    3: "DSG_OT 放电过温保护",
    4: "RCA 剩余容量保护",
    5: "DSG_UT 放电低温保护",
    8: "COV 单体电池过压",
    9: "OCC 充电过流",
    10: "CHG_OT 充电过温保护",
    11: "CHG_UT 充电低温保护",
}

BATTERY_SAFETY_BITS = {
    0: "CUV 安全-单体电池欠压",
    1: "OCD 安全-放电过流",
    2: "SCD 安全-电池短路",
    3: "DSG_OT 安全-放电过温",
    4: "RCA 安全-剩余容量",
    5: "DSG_UT 安全-放电低温",
    8: "COV 安全-单体电池过压",
    9: "OCC 安全-充电过流",
    10: "CHG_OT 安全-充电过温",
    11: "CHG_UT 安全-充电低温",
}


def _decode_bits(val: int, bit_map: dict) -> list[str]:
    msgs = []
    for bit, desc in bit_map.items():
        if val & (1 << bit):
            msgs.append(desc)
    return msgs


def decode_battery_alarm(val: int) -> list[str]:
    if val == 0:
        return []
    return _decode_bits(val, BATTERY_ALARM_BITS)


def decode_battery_safety(val: int) -> list[str]:
    if val == 0:
        return []
    return _decode_bits(val, BATTERY_SAFETY_BITS)


def append_log_line(line: str):
    """
    将异常信息追加写入限制大小的日志文件：
    <脚本目录>/battrey.txt
    """
    log_dir = os.path.dirname(LOG_PATH)
    try:
        os.makedirs(log_dir, exist_ok=True)

        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > MAX_LOG_SIZE:
            # 简单截断：只保留文件末尾一半内容
            try:
                with open(LOG_PATH, "r", encoding="utf-8") as f:
                    data = f.read()
                # 取后半部分
                keep = data[-(MAX_LOG_SIZE // 2):]
                with open(LOG_PATH, "w", encoding="utf-8") as f:
                    f.write(keep)
            except OSError:
                # 读写失败则直接覆盖
                pass

        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        # 磁盘/权限问题时，不影响主程序运行
        return


def init_log_file():
    """
    确保日志目录与文件存在（脚本所在目录）：
    - 创建脚本目录（一般已存在）
    - 若 battrey.txt 不存在，则写入一行简单的头信息
    """
    log_dir = os.path.dirname(LOG_PATH)
    try:
        os.makedirs(log_dir, exist_ok=True)
        if not os.path.exists(LOG_PATH):
            with open(LOG_PATH, "w", encoding="utf-8") as f:
                f.write("===== BMS 电池安全监测日志 =====\n")
    except OSError:
        # 创建失败时忽略，不影响主程序
        return


async def send_cloud_websocket(pack_v: float, current_a: float, soc: int, tmax_c: float, seq: int):
    """
    通过 WebSocket 向云端上报一次电池状态。
    - 默认地址: ws://43.143.74.209:3000/ws （可用环境变量 BMS_WS_URL 覆盖）
    - 设备 UUID: c1012 （可用环境变量 BMS_WS_UUID 覆盖）
    - 数据格式与 websocket_client_1.py 保持一致
    """
    global _ws_client, _ws_connected, _ws_warned

    if not CLOUD_WS_URL:
        if not _ws_warned:
            print("云端 WebSocket 未配置（CLOUD_WS_URL 为空）")
            _ws_warned = True
        return

    # 构建 WebSocket URI，添加 type=device 和 uuid 参数
    sep = "&" if "?" in CLOUD_WS_URL else "?"
    uri = f"{CLOUD_WS_URL}{sep}type=device&uuid={WS_UUID}"

    # 如果未连接，尝试连接
    if not _ws_connected or _ws_client is None:
        try:
            _ws_client = await websockets.connect(uri)
            _ws_connected = True
            _ws_warned = False
            print(f"[WebSocket] 已连接到云端: {uri} (uuid={WS_UUID})")
        except (OSError, Exception) as e:
            if not _ws_warned:
                print(f"[WebSocket] 连接失败: {e}，将重试...")
                _ws_warned = True
            _ws_connected = False
            return

    # 构建上报数据，格式与 websocket_client_1.py 保持一致
    payload = {
        "uuid": WS_UUID,
        "type": "telemetry",
        "kind": "temperature",
        "value": round(tmax_c, 1),  # 使用最高温度作为 temperature
        "current": round(current_a, 2),
        "batteryPercent": soc,
        "batteryMaxTemp": round(tmax_c, 1),
        "batteryVoltage": round(pack_v, 1),
        "seq": seq,
        "message": (
            f"设备{WS_UUID}温度={tmax_c:.1f}℃, 电流={current_a:.2f}A, "
            f"电量={soc}%, 最高温度={tmax_c:.1f}℃, "
            f"电压={pack_v:.1f}V (第 {seq} 次上报)"
        ),
    }

    try:
        text = json.dumps(payload, ensure_ascii=False)
        await _ws_client.send(text)
        if not _ws_warned:
            print(f"[WebSocket] 数据上报成功: seq={seq}")
    except (ConnectionClosedError, ConnectionClosedOK, OSError) as e:
        _ws_connected = False
        _ws_client = None
        if not _ws_warned:
            print(f"[WebSocket] 连接断开: {e}，将重连...")
            _ws_warned = True
    except Exception as e:
        if not _ws_warned:
            print(f"[WebSocket] 发送失败: {e}")
            _ws_warned = True


def read_status_once(ser):
    """
    读取一次关键状态：
    - PACK 总电压 (V)
    - 电池电流 (A)
    - SOC (%)
    - 最高温度 (°C)
    返回 (pack_v, current_a, soc, tmax_c) 或 None（失败）
    """
    # 读 0x0400 开始的一段 PACK 信息
    regs = modbus_read_regs(ser, 0x0400, 0x16)
    if not regs or len(regs) < 0x16:
        return None

    # 按通信协议解析
    # 0x0400 / 0x0401 -> Current_L / Current_H, 单位 mA long（有符号）
    current_ma = s32(regs[0], regs[1])
    current_a = current_ma / 1000.0

    # 0x040A / 0x040B -> PACK Voltage_L / PACK Voltage_H, 单位 mV long
    pack_mv = u32(regs[11 - 1], regs[12 - 1])  # 即 regs[10], regs[11]
    pack_v = pack_mv / 1000.0

    # 0x0411 -> SOC (%)
    soc = regs[0x0411 - 0x0400]  # 即 regs[17]

    # 0x0413 / 0x0414 / 0x0415 -> BatteryStatus / BatteryAlarm / BatterySafety
    batt_status = regs[0x0413 - 0x0400]
    batt_alarm = regs[0x0414 - 0x0400]
    batt_safety = regs[0x0415 - 0x0400]

    # 最高温度：0x0C00 (Temp MAX)，单位 0.1K
    tmax_regs = modbus_read_regs(ser, 0x0C00, 1)
    if not tmax_regs:
        return None
    tmax_raw = tmax_regs[0]
    tmax_c = (tmax_raw - 2731) / 10.0

    return pack_v, current_a, soc, tmax_c, batt_status, batt_alarm, batt_safety


async def websocket_receiver():
    """
    WebSocket 接收协程：接收来自 Web 端的消息
    """
    global _ws_client, _ws_connected

    while True:
        if _ws_connected and _ws_client:
            try:
                async for msg in _ws_client:
                    print(f"[WebSocket] 收到来自 Web 的消息: {msg}")
                    try:
                        data = json.loads(msg)
                        if "state" in data:
                            print(f"[WebSocket] 状态切换为: {data['state']}")
                    except json.JSONDecodeError:
                        continue
            except (ConnectionClosedError, ConnectionClosedOK, OSError):
                _ws_connected = False
                _ws_client = None
                await asyncio.sleep(5)
        else:
            await asyncio.sleep(1)


async def main_async(ser):
    """
    异步主循环：读取 BMS 数据、显示、记录日志、HTTP 上报、WebSocket 上报
    """
    global _ws_client

    print("🔋 BMS 安全监测已启动，按 Ctrl+C 退出。\n")
    print(f"WebSocket 地址: {CLOUD_WS_URL} (uuid={WS_UUID})\n")

    # 启动 WebSocket 接收协程（后台运行）
    receiver_task = asyncio.create_task(websocket_receiver())

    seq = 1
    try:
        while True:
            # 读取 BMS 数据（同步操作，在事件循环中运行）
            status = read_status_once(ser)
            if status is None:
                print("读取 BMS 数据失败，检查连接与地址/波特率设置。")
                await asyncio.sleep(1)
                continue

            pack_v, current_a, soc, tmax_c, batt_status, batt_alarm, batt_safety = status

            # 阈值类告警
            alarms = check_alarms(pack_v, current_a, soc, tmax_c)

            # 根据通信协议解码 BatteryAlarm / BatterySafety
            alarms.extend(decode_battery_alarm(batt_alarm))
            alarms.extend(decode_battery_safety(batt_safety))

            # 电流方向说明：约定 >0 为充电，<0 为放电
            if current_a > 0:
                cur_mode = "充电"
            elif current_a < 0:
                cur_mode = "放电"
            else:
                cur_mode = "静止"
            cur_abs = abs(current_a)

            now = time.strftime("%Y-%m-%d %H:%M:%S")
            if alarms:
                alarm_text = " | 告警: " + "；".join(alarms)
            else:
                alarm_text = " | 状态: 正常"

            line = (
                f"[{now}] "
                f"PACK 总电压: {pack_v:6.2f} V | "
                f"电池电流: {cur_mode} {cur_abs:6.2f} A | "
                f"SOC: {soc:3d} % | "
                f"最高温度: {tmax_c:5.1f} ℃"
                f"{alarm_text}"
            )

            print(line)

            # 写入限制大小的日志文件（无论正常/告警，全部记录）
            append_log_line(line)

            # 通过 WebSocket 上报数据
            await send_cloud_websocket(pack_v, current_a, soc, tmax_c, seq)
            seq += 1

            # 每 5 秒采样/写入一次
            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("\n退出监测。")
    finally:
        # 关闭 WebSocket 连接
        receiver_task.cancel()
        if _ws_client:
            try:
                await _ws_client.close()
            except Exception:
                pass


def main():
    # 确保日志目录与文件存在
    init_log_file()

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=TIMEOUT,
    )

    try:
        # 运行异步主循环
        asyncio.run(main_async(ser))
    except KeyboardInterrupt:
        print("\n退出监测。")
    finally:
        ser.close()


if __name__ == "__main__":
    main()


