#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过串口 Modbus 读取 BMS 全部可读参数（协议功能码 03 + 0x11 BMS ID），结果写入 test_all.txt
支持持续监测模式：电池温度 + 电脑温度（CPU、NVMe），合并输出。
依赖: pip install pyserial；监测电脑温度需系统有 sensors（lm-sensors）
"""

import sys
import serial
import struct
import time
from pathlib import Path

try:
    from test_system_temp import (
        get_cpu_temp,
        get_nvme_temp,
        log_msg,
        CPU_WARN,
        NVME_WARN,
        INTERVAL as TEMP_INTERVAL,
    )
except ImportError:
    get_cpu_temp = get_nvme_temp = log_msg = None
    CPU_WARN = NVME_WARN = 85
    TEMP_INTERVAL = 2

SCRIPT_DIR = Path(__file__).resolve().parent
PORT = "/dev/ttyCH341USB1"
BAUDRATE = 9600
ADDR = 0x0B
TIMEOUT = 0.5
OUT_FILE = SCRIPT_DIR / "test_all.txt"

# 协议中可读寄存器范围（功能码 03）
PACK_START, PACK_COUNT = 0x0400, 0x16
VOLT_START, VOLT_COUNT = 0x0800, 16
TEMP_START, TEMP_COUNT = 0x0C00, 4
AFE_START, AFE_COUNT = 0x1000, 3


def crc16_modbus(data: bytes) -> int:
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
    frame = struct.pack(">B B H H", ADDR, 0x03, start_addr, count)
    crc = crc16_modbus(frame)
    frame += struct.pack("<H", crc)
    ser.reset_input_buffer()
    ser.write(frame)
    resp = ser.read(5 + count * 2)
    if len(resp) < 5:
        return None
    if resp[0] != ADDR or resp[1] != 0x03:
        return None
    crc_recv = struct.unpack("<H", resp[-2:])[0]
    if crc_recv != crc16_modbus(resp[:-2]):
        return None
    data = resp[3:-2]
    return [struct.unpack(">H", data[i : i + 2])[0] for i in range(0, len(data), 2)]


def modbus_read_bms_id(ser):
    """功能码 0x11，读 BMS ID，12 字节。先试 0x11 + 起始 0x0000 + 长度 6 字。"""
    for attempt in [
        struct.pack(">B B H H", ADDR, 0x11, 0x0000, 0x0006),
        struct.pack(">B B", ADDR, 0x11),
    ]:
        frame = attempt + struct.pack("<H", crc16_modbus(attempt))
        ser.reset_input_buffer()
        ser.write(frame)
        time.sleep(0.05)
        resp = ser.read(256)
        if len(resp) >= 2 and resp[0] == ADDR and resp[1] == 0x11:
            if len(resp) >= 4 + 2:
                n = resp[2]
                if n == 12 and len(resp) >= 3 + 12 + 2:
                    payload = resp[3 : 3 + 12]
                    if crc16_modbus(resp[: 3 + 12]) == struct.unpack("<H", resp[3 + 12 : 3 + 14])[0]:
                        return payload
                if n == 0x0C and len(resp) >= 17:
                    payload = resp[3:15]
                    if crc16_modbus(resp[:15]) == struct.unpack("<H", resp[15:17])[0]:
                        return payload
            if len(resp) >= 17:
                payload = resp[3:15]
                if crc16_modbus(resp[:15]) == struct.unpack("<H", resp[15:17])[0]:
                    return payload
    return None


def u32(lo: int, hi: int) -> int:
    return (hi << 16) | lo


def s32(lo: int, hi: int) -> int:
    val = (hi << 16) | lo
    if val & 0x80000000:
        val -= 0x100000000
    return val


def write(f, text: str = ""):
    f.write(text + "\n")
    print(text)


def _fmt_time(v):
    return "N/A" if v == 65535 else f"{v} min"


def read_bms_temps_c(ser):
    """读取 BMS 温度寄存器，返回 [MAX, MIN, Temp1, Temp2] 单位 ℃，失败返回 None"""
    r = modbus_read_regs(ser, TEMP_START, TEMP_COUNT)
    if not r:
        return None
    return [(v - 2731) / 10 for v in r]


def read_bms_soc_and_current(ser):
    """读取 PACK 前 2 个寄存器（电流 L/H）和 SOC，返回 (soc_percent, current_mA)。失败返回 (None, None)"""
    r = modbus_read_regs(ser, PACK_START, 0x12)
    if not r or len(r) < 18:
        return (None, None)
    current_mA = s32(r[0], r[1])
    soc = r[17]
    return (soc, current_mA)


def _fmt_bms_id_ascii(b):
    return "".join(c if 32 <= ord(c) < 127 else "" for c in b.decode("latin-1")).strip() or "—"


def _decode_battery_status(v):
    """BatteryStatus 位 → 中文"""
    names = [
        "容量自修正", "循环计数", "内阻更新", "电池放空", "电池充满", "休眠",
        "AFE数据读取", "剩余时间", "OCV修正", "LED指示", "弱电开关", "保留",
        "校准使能", "CC偏移", "通讯中", "程序激活",
    ]
    return _bits_to_names(v, names)


def _decode_alarm_safety(v):
    """BatteryAlarm / BatterySafety / AFE保护 位 → 中文"""
    names = [
        "单节欠压", "放电过流", "短路", "放电过温", "剩余容量保护", "放电低温",
        "保留", "保留", "单节过压", "充电过流", "充电过温", "充电低温",
        "保留", "保留", "保留", "告警",
    ]
    return _bits_to_names(v, names)


def _decode_afe_status(v):
    """AFE 状态位 → 中文"""
    names = [
        "充电MOS", "放电MOS", "预充", "中断", "电压中断", "温度中断", "电流中断",
        "负载", "充电器", "放电中", "充电中", "通讯", "看门狗", "均衡开", "唤醒", "休眠",
    ]
    return _bits_to_names(v, names)


def _decode_afe_safety(v):
    """AFE 保护位 → 中文"""
    names = [
        "过压", "短路", "欠压", "充电过流", "放电过流1", "放电过流2",
        "放电低温", "放电高温", "充电低温", "充电高温",
    ]
    return _bits_to_names(v, names[:10])


def _bits_to_names(val, names):
    """按位取 1 的名称列表，用空格拼成一句"""
    out = []
    for i, name in enumerate(names):
        if i < 16 and (val >> i) & 1:
            out.append(name)
    return " ".join(out) if out else "无"


def main():
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=TIMEOUT,
    )

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        write(f, "===== BMS 全参数扫描结果（test_all.py 实际读取） =====\n")

        # ---------- BMS ID -----------
        write(f, "[设备]")
        bms_id = modbus_read_bms_id(ser)
        if bms_id:
            write(f, f"  设备ID  {_fmt_bms_id_ascii(bms_id)}")
        else:
            write(f, "  设备ID  未读取到")

        # ---------- PACK 信息 0x0400-0x0415 ----------
        write(f, "\n[PACK 信息]")
        regs = modbus_read_regs(ser, PACK_START, PACK_COUNT)
        if regs:
            current = s32(regs[0], regs[1])
            rem_cap = u32(regs[2], regs[3])
            full_cap = u32(regs[4], regs[5])
            charge_current = u32(regs[6], regs[7])
            charge_voltage = u32(regs[8], regs[9])
            pack_voltage = u32(regs[10], regs[11])
            batt_voltage = u32(regs[12], regs[13])
            cycle = regs[14]
            t_empty = regs[15]
            t_full = regs[16]
            soc = regs[17]
            soh = regs[18]
            battery_status = regs[19]
            battery_alarm = regs[20]
            battery_safety = regs[21]

            L = 20
            write(f, f"  {'电池电流':<{L}} {current / 1000:>6.2f} A")
            write(f, f"  {'剩余容量':<{L}} {rem_cap:>6} mAh")
            write(f, f"  {'满充容量':<{L}} {full_cap:>6} mAh")
            write(f, f"  {'充电电流':<{L}} {charge_current / 1000:>6.2f} A")
            write(f, f"  {'充电电压':<{L}} {charge_voltage / 1000:>6.2f} V")
            write(f, f"  {'PACK 总电压':<{L}} {pack_voltage / 1000:>6.2f} V")
            write(f, f"  {'电池电压':<{L}} {batt_voltage / 1000:>6.2f} V")
            write(f, f"  {'循环次数':<{L}} {cycle:>6}")
            write(f, f"  {'剩余可用时间':<{L}} {_fmt_time(t_empty):>6}")
            write(f, f"  {'充满所需时间':<{L}} {_fmt_time(t_full):>6}")
            write(f, f"  {'SOC':<{L}} {soc:>6} %")
            write(f, f"  {'SOH':<{L}} {soh:>6} %")
            write(f, f"  {'电池状态':<{L}} {_decode_battery_status(battery_status)}")
            write(f, f"  {'告警':<{L}} {_decode_alarm_safety(battery_alarm)}")
            write(f, f"  {'保护':<{L}} {_decode_alarm_safety(battery_safety)}")
        else:
            write(f, "  读取失败（请检查串口、地址与接线）")

        # ---------- 单体电压 0x0800-0x080F+ ----------
        write(f, "\n[单体电压]")
        vregs = modbus_read_regs(ser, VOLT_START, VOLT_COUNT)
        if vregs:
            write(f, f"  最高  {vregs[0]:>5} mV    最低  {vregs[1]:>5} mV")
            for i in range(2, VOLT_COUNT):
                val = vregs[i]
                cell = f"Cell {i - 1:02d}"
                s = f"{val} mV" if val else "—"
                write(f, f"  {cell}  {s:>10}")
        else:
            write(f, "  读取失败")

        # ---------- 温度 0x0C00-0x0C03 ----------
        write(f, "\n[温度]")
        tregs = modbus_read_regs(ser, TEMP_START, TEMP_COUNT)
        if tregs:
            labels = ["MAX", "MIN", "Temp1", "Temp2"]
            parts = [f"{labels[i]} {(tregs[i] - 2731) / 10:.1f} ℃" for i in range(TEMP_COUNT)]
            write(f, "  " + "    ".join(parts))
        else:
            write(f, "  读取失败")

        # ---------- 状态（人可读）----------
        write(f, "\n[状态]")
        afe_status = modbus_read_regs(ser, 0x1000, 1)
        afe_safety = modbus_read_regs(ser, 0x1001, 1)
        balance = modbus_read_regs(ser, 0x1002, 1)
        if afe_status is not None and afe_safety is not None and balance is not None:
            write(f, f"  运行   {_decode_afe_status(afe_status[0])}")
            write(f, f"  保护   {_decode_afe_safety(afe_safety[0])}")
            write(f, f"  均衡   {'均衡中' if balance[0] else '未均衡'}")
        else:
            write(f, "  读取失败")

        write(f, "\n===== 扫描结束 =====")

    ser.close()
    print(f"结果已写入: {OUT_FILE}")


def run_monitor():
    """持续监测：电池温度 + 电脑温度，合并输出；超阈值写日志告警。"""
    print("持续监测温度（电池 + CPU + NVMe），按 Ctrl+C 退出\n")
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=TIMEOUT,
        )
    except Exception as e:
        print(f"串口打开失败: {e}，仅显示电脑温度")
        ser = None
    if log_msg:
        log_msg("BMS+系统温度监测已启动")

    try:
        while True:
            parts = []
            # 电池：百分比 + 是否充电 + 温度（范围，直观）
            if ser is not None:
                soc, current_mA = read_bms_soc_and_current(ser)
                bms = read_bms_temps_c(ser)
                soc_s = f"{soc}%" if soc is not None else "—"
                if current_mA is not None:
                    if current_mA > 0:
                        charge_s = "充电中"
                    elif current_mA < 0:
                        charge_s = "放电中"
                    else:
                        charge_s = "静置"
                else:
                    charge_s = ""
                if bms is not None:
                    t_min, t_max = min(bms), max(bms)
                    if t_min == t_max:
                        temp_s = f"{t_min:.0f}℃"
                    else:
                        temp_s = f"{t_min:.0f}~{t_max:.0f}℃"
                else:
                    temp_s = "—"
                battery_part = f"电池 {soc_s} {charge_s} {temp_s}".strip()
                parts.append(battery_part)
            else:
                parts.append("电池 —")
            # 电脑温度
            if get_cpu_temp is not None and get_nvme_temp is not None:
                cpu = get_cpu_temp()
                nvme = get_nvme_temp()
                cpu_s = f"{cpu:.1f}" if cpu is not None else "—"
                nvme_s = f"{nvme:.1f}" if nvme is not None else "—"
                parts.append(f"CPU {cpu_s}℃")
                parts.append(f"NVMe {nvme_s}℃")
                if log_msg:
                    if cpu is not None and cpu > CPU_WARN:
                        log_msg(f"WARNING: CPU 过热 {cpu:.1f}°C")
                        print("  ⚠ CPU 过热!")
                    if nvme is not None and nvme > NVME_WARN:
                        log_msg(f"WARNING: NVMe 过热 {nvme:.1f}°C")
                        print("  ⚠ NVMe 过热!")
            else:
                parts.append("CPU/NVMe(未安装 test_system_temp 或 sensors)")

            line = " | ".join(parts)
            ts = time.strftime("%H:%M:%S", time.localtime())
            print(f"[{ts}] {line}")
            time.sleep(TEMP_INTERVAL)
    except KeyboardInterrupt:
        print("\n监测已停止")
    finally:
        if ser is not None:
            ser.close()


if __name__ == "__main__":
    if "--monitor" in sys.argv or "monitor" in sys.argv:
        run_monitor()
    else:
        main()
