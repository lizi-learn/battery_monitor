import serial
import struct
import time

PORT = "/dev/ttyCH341USB1"   # ← 你已经验证是这个
BAUDRATE = 9600
ADDR = 0x0B
TIMEOUT = 1


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def modbus_read(ser, start_addr, count):
    frame = struct.pack(">B B H H", ADDR, 0x03, start_addr, count)
    crc = crc16_modbus(frame)
    frame += struct.pack("<H", crc)

    ser.write(frame)

    # 期望返回：addr + func + bytes + data + crc
    resp_len = 5 + count * 2
    resp = ser.read(resp_len)

    if len(resp) != resp_len:
        raise RuntimeError("Modbus response length error")

    if resp[0] != ADDR or resp[1] != 0x03:
        raise RuntimeError("Modbus response header error")

    crc_recv = struct.unpack("<H", resp[-2:])[0]
    crc_calc = crc16_modbus(resp[:-2])
    if crc_recv != crc_calc:
        raise RuntimeError("CRC error")

    data = resp[3:-2]
    regs = []
    for i in range(0, len(data), 2):
        regs.append(struct.unpack(">H", data[i:i+2])[0])

    return regs


def read_pack_voltage(ser):
    regs = modbus_read(ser, 0x040A, 2)
    mv = (regs[1] << 16) | regs[0]
    return mv / 1000.0  # V


def read_remaining_capacity(ser):
    regs = modbus_read(ser, 0x0402, 2)
    mah = (regs[1] << 16) | regs[0]
    return mah / 1000.0  # Ah


def read_full_capacity(ser):
    regs = modbus_read(ser, 0x0404, 2)
    mah = (regs[1] << 16) | regs[0]
    return mah / 1000.0  # Ah


def read_soc(ser):
    regs = modbus_read(ser, 0x0411, 1)
    return regs[0]  # %


def main():
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=TIMEOUT,
    )

    print("🔋 BMS Monitor Started")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            voltage = read_pack_voltage(ser)
            soc = read_soc(ser)
            rem_cap = read_remaining_capacity(ser)
            full_cap = read_full_capacity(ser)

            print(
                f"PACK Voltage : {voltage:.3f} V\n"
                f"SOC          : {soc:.1f} %\n"
                f"RemainingCap : {rem_cap:.3f} Ah\n"
                f"FullCapacity : {full_cap:.3f} Ah\n"
                "-------------------------------"
            )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nExit.")
    finally:
        ser.close()


if __name__ == "__main__":
    main()
