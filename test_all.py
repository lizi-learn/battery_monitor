#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通过串口 Modbus 读取 BMS 全部可读参数（协议功能码 03 + 0x11 BMS ID），结果写入 test_all.txt
依赖: pip install pyserial
"""

import serial
import struct
import time
from pathlib import Path

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

        # ---------- BMS ID（功能码 0x11）----------
        write(f, "[BMS ID]")
        bms_id = modbus_read_bms_id(ser)
        if bms_id:
            try:
                write(f, f"ASCII : {bms_id.decode('ascii', errors='replace').strip()}")
            except Exception:
                pass
            write(f, f"HEX   : {bms_id.hex().upper()}")
        else:
            write(f, "未读取到（部分设备不支持 0x11）")

        # ---------- PACK 信息 0x0400-0x0415 ----------
        write(f, "\n[PACK 信息] 寄存器 0x0400-0x0415")
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

            write(f, f"Current_L/H       : {current} mA ({current / 1000:.2f} A)")
            write(f, f"RemainingCapacity : {rem_cap} mAh")
            write(f, f"FullChargeCapacity: {full_cap} mAh")
            write(f, f"Charge Current    : {charge_current} mA ({charge_current / 1000:.2f} A)")
            write(f, f"ChargingVoltage   : {charge_voltage} mV ({charge_voltage / 1000:.2f} V)")
            write(f, f"PACK Voltage      : {pack_voltage} mV ({pack_voltage / 1000:.2f} V)")
            write(f, f"BatteryVoltage    : {batt_voltage} mV ({batt_voltage / 1000:.2f} V)")
            write(f, f"Cycle_Count       : {cycle}")
            write(f, f"AverageTimeToEmpty: {t_empty} min")
            write(f, f"AverageTimeToFull : {t_full} min")
            write(f, f"SOC               : {soc} %")
            write(f, f"SOH               : {soh} %")
            write(f, f"BatteryStatus     : 0x{battery_status:04X}")
            write(f, f"BatteryAlarm      : 0x{battery_alarm:04X}")
            write(f, f"BatterySafety     : 0x{battery_safety:04X}")
        else:
            write(f, "读取失败（请检查串口、地址与接线）")

        # ---------- 单体电压 0x0800-0x080F+ ----------
        write(f, "\n[单体电压] 寄存器 0x0800-0x080F+")
        vmax = modbus_read_regs(ser, 0x0800, 1)
        vmin = modbus_read_regs(ser, 0x0801, 1)
        if vmax and vmin:
            write(f, f"Voltage Max       : {vmax[0]} mV")
            write(f, f"Voltage Min       : {vmin[0]} mV")
        for i in range(2, VOLT_COUNT):
            v = modbus_read_regs(ser, 0x0800 + i, 1)
            if v:
                write(f, f"Voltage {i - 1:2d} (Cell {i - 1:02d}): {v[0]} mV")

        # ---------- 温度 0x0C00-0x0C03+，协议：Temp MAX/MIN/Temp1/Temp2... ----------
        write(f, "\n[温度信息] 寄存器 0x0C00-0x0C03+ (℃=(值-2731)/10)")
        for i in range(TEMP_COUNT):
            t = modbus_read_regs(ser, TEMP_START + i, 1)
            if t:
                temp_c = (t[0] - 2731) / 10
                label = ["Temp MAX", "Temp MIN", "Temp1", "Temp2"][i] if i < 4 else f"Temp{i}"
                write(f, f"{label:12s} 0x{TEMP_START + i:04X}: {t[0]} (0x{t[0]:04X}) = {temp_c:.1f} ℃")

        # ---------- AFE 0x1000, 0x1001, 0x1002 ----------
        write(f, "\n[状态信息] AFE 寄存器 0x1000-0x1002")
        afe_status = modbus_read_regs(ser, 0x1000, 1)
        afe_safety = modbus_read_regs(ser, 0x1001, 1)
        balance = modbus_read_regs(ser, 0x1002, 1)
        if afe_status:
            write(f, f"AFE Status 0x1000 : 0x{afe_status[0]:04X}")
        if afe_safety:
            write(f, f"AFE Safety 0x1001: 0x{afe_safety[0]:04X}")
        if balance:
            write(f, f"CELL BALAN 0x1002: 0x{balance[0]:04X}")

        # ---------- 原始寄存器摘要（协议中所有可读地址）----------
        write(f, "\n[原始寄存器摘要]")
        for name, start, count in [
            ("0x0400 PACK", PACK_START, PACK_COUNT),
            ("0x0800 电压", VOLT_START, VOLT_COUNT),
            ("0x0C00 温度", TEMP_START, TEMP_COUNT),
            ("0x1000 AFE", AFE_START, AFE_COUNT),
        ]:
            r = modbus_read_regs(ser, start, count)
            if r:
                write(f, f"  {name}: " + " ".join(f"{x:04X}" for x in r))
            else:
                write(f, f"  {name}: 读取失败")

        write(f, "\n===== 扫描结束 =====")

    ser.close()
    print(f"结果已写入: {OUT_FILE}")


if __name__ == "__main__":
    main()
