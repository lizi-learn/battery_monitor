"""
Modbus RTU 通信客户端模块
提供与 BMS 设备的 Modbus 通信功能
"""

import struct
import serial
from typing import Optional, List


class ModbusClient:
    """Modbus RTU 客户端"""
    
    def __init__(self, port: str, baudrate: int = 9600, address: int = 0x0B, 
                 timeout: float = 0.5, bytesize: int = 8, parity: str = "N", 
                 stopbits: int = 1):
        """
        初始化 Modbus 客户端
        
        Args:
            port: 串口设备路径
            baudrate: 波特率
            address: Modbus 设备地址
            timeout: 超时时间（秒）
            bytesize: 数据位
            parity: 校验位
            stopbits: 停止位
        """
        self.port = port
        self.baudrate = baudrate
        self.address = address
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        self.ser: Optional[serial.Serial] = None
    
    def connect(self) -> bool:
        """连接串口"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
            return True
        except Exception as e:
            print(f"连接串口失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.ser = None
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.ser is not None and self.ser.is_open
    
    @staticmethod
    def crc16_modbus(data: bytes) -> int:
        """
        CRC-16/MODBUS 计算
        
        Args:
            data: 待计算的数据
            
        Returns:
            CRC16 校验值
        """
        crc = 0xFFFF
        for b in data:
            crc ^= b
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc & 0xFFFF
    
    def read_registers(self, start_addr: int, count: int) -> Optional[List[int]]:
        """
        读取保持寄存器（功能码 0x03）
        
        Args:
            start_addr: 起始地址
            count: 读取数量
            
        Returns:
            寄存器值列表，失败返回 None
        """
        if not self.is_connected():
            return None
        
        # 构造请求帧
        frame = struct.pack(">B B H H", self.address, 0x03, start_addr, count)
        crc = self.crc16_modbus(frame)
        frame += struct.pack("<H", crc)
        
        try:
            # 清空输入缓冲区
            self.ser.reset_input_buffer()
            self.ser.write(frame)
            
            # 读取响应
            resp_len = 5 + count * 2
            resp = self.ser.read(resp_len)
            
            if len(resp) < 5:
                return None
            
            # 检查地址和功能码
            if resp[0] != self.address or resp[1] != 0x03:
                return None
            
            # CRC 校验
            crc_recv = struct.unpack("<H", resp[-2:])[0]
            if crc_recv != self.crc16_modbus(resp[:-2]):
                return None
            
            # 解析数据
            data = resp[3:-2]
            regs = [
                struct.unpack(">H", data[i:i + 2])[0]
                for i in range(0, len(data), 2)
            ]
            return regs
            
        except Exception as e:
            print(f"读取寄存器失败: {e}")
            return None
    
    @staticmethod
    def u32(lo: int, hi: int) -> int:
        """
        将两个 16bit 寄存器合成为无符号 32bit
        
        Args:
            lo: 低16位
            hi: 高16位
            
        Returns:
            32位无符号整数
        """
        return (hi << 16) | lo
    
    @staticmethod
    def s32(lo: int, hi: int) -> int:
        """
        将两个 16bit 寄存器合成为有符号 32bit
        
        Args:
            lo: 低16位
            hi: 高16位
            
        Returns:
            32位有符号整数
        """
        val = (hi << 16) | lo
        if val & 0x80000000:
            val -= 0x100000000
        return val
    
    def __enter__(self):
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.disconnect()

