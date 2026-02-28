import serial
import struct
import time

PORT = "/dev/ttyCH341USB1"
BAUDRATE = 9600
ADDR = 0x0B
TIMEOUT = 0.5
OUT_FILE = "all.txt"


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


def modbus_read_regs(ser, start_addr, count):
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
    regs = [struct.unpack(">H", data[i:i + 2])[0]
            for i in range(0, len(data), 2)]
    return regs


def u32(lo, hi):
    return (hi << 16) | lo


def s32(lo, hi):
    """按有符号 32bit long 解码（用于电池电流 Current）"""
    val = (hi << 16) | lo
    if val & 0x80000000:
        val -= 0x100000000
    return val


def write(f, text=""):
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
        write(f, "===== BMS 全参数扫描结果 =====\n")

        # -------- PACK 信息 --------
        write(f, "[PACK 信息]")
        regs = modbus_read_regs(ser, 0x0400, 0x16)
        if regs:
            # 电池电流 Current 为有符号 long，需按有符号 32bit 解码
            current = s32(regs[0], regs[1])
            rem_cap = u32(regs[2], regs[3])
            full_cap = u32(regs[4], regs[5])
            charge_current = u32(regs[6], regs[7])
            charge_voltage = u32(regs[8], regs[9])
            pack_voltage = u32(regs[10], regs[11])
            batt_voltage = regs[12]
            cycle = regs[14]
            t_empty = regs[15]
            t_full = regs[16]
            soc = regs[17]
            soh = regs[18]

            write(f, f"电池电流        : {current / 1000:.2f} A")
            write(f, f"剩余容量        : {rem_cap} mAh")
            write(f, f"满充容量        : {full_cap} mAh")
            write(f, f"充电电流        : {charge_current / 1000:.2f} A")
            write(f, f"充电电压        : {charge_voltage / 1000:.2f} V")
            write(f, f"PACK 总电压     : {pack_voltage / 1000:.2f} V")
            write(f, f"电池电压        : {batt_voltage / 1000:.2f} V")
            write(f, f"循环次数        : {cycle}")
            write(f, f"剩余可用时间    : {t_empty} min")
            write(f, f"充满所需时间    : {t_full} min")
            write(f, f"SOC             : {soc} %")
            write(f, f"SOH             : {soh} %")

        write(f, "\n[单体电压]")
        vmax = modbus_read_regs(ser, 0x0800, 1)
        vmin = modbus_read_regs(ser, 0x0801, 1)
        if vmax and vmin:
            write(f, f"最高单体电压    : {vmax[0]} mV")
            write(f, f"最低单体电压    : {vmin[0]} mV")

        for i in range(2, 16):
            v = modbus_read_regs(ser, 0x0800 + i, 1)
            if v:
                write(f, f"Cell {i - 1:02d} 电压      : {v[0]} mV")

        write(f, "\n[温度信息]")
        for i in range(0, 4):
            t = modbus_read_regs(ser, 0x0C00 + i, 1)
            if t:
                temp_c = (t[0] - 2731) / 10
                write(f, f"温度 {i}          : {temp_c:.1f} ℃")

        write(f, "\n[状态信息]")
        afe_status = modbus_read_regs(ser, 0x1000, 1)
        afe_safety = modbus_read_regs(ser, 0x1001, 1)
        balance = modbus_read_regs(ser, 0x1002, 1)

        if afe_status:
            write(f, f"AFE 状态        : 0x{afe_status[0]:04X}")
        if afe_safety:
            write(f, f"AFE 安全        : 0x{afe_safety[0]:04X}")
        if balance:
            write(f, f"均衡状态        : 0x{balance[0]:04X}")

        write(f, "\n===== 扫描结束 =====")

    ser.close()


if __name__ == "__main__":
    main()
