"""
BMS 全参数扫描工具
扫描并输出所有 BMS 参数
"""

import os
import sys
import yaml
from pathlib import Path

from .modbus_client import ModbusClient
from .bms_parser import BMSParser


class BMSScanner:
    """BMS 扫描器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化扫描器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.client: ModbusClient = None
        self.parser = BMSParser()
        self.output_file = self._get_output_file()
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_output_file(self) -> str:
        """获取输出文件路径"""
        log_dir = self.config.get("logging", {}).get("log_dir", "logs")
        log_file = self.config.get("logging", {}).get("scan_log_file", "bms_scan.log")
        
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, log_file)
    
    def _write(self, f, text: str = ""):
        """写入文件并打印"""
        f.write(text + "\n")
        print(text)
    
    def scan(self):
        """执行扫描"""
        serial_cfg = self.config.get("serial", {})
        modbus_cfg = self.config.get("modbus", {})
        reg_cfg = self.config.get("registers", {})
        
        self.client = ModbusClient(
            port=serial_cfg.get("port", "/dev/ttyCH341USB0"),
            baudrate=serial_cfg.get("baudrate", 9600),
            address=modbus_cfg.get("address", 0x0B),
            timeout=serial_cfg.get("timeout", 0.5),
            bytesize=serial_cfg.get("bytesize", 8),
            parity=serial_cfg.get("parity", "N"),
            stopbits=serial_cfg.get("stopbits", 1),
        )
        
        if not self.client.connect():
            print("连接串口失败")
            return
        
        with open(self.output_file, "w", encoding="utf-8") as f:
            self._write(f, "===== BMS 全参数扫描结果 =====\n")
            
            # PACK 信息
            self._write(f, "[PACK 信息]")
            pack_start = reg_cfg.get("pack_info_start", 0x0400)
            pack_count = reg_cfg.get("pack_info_count", 0x16)
            pack_regs = self.client.read_registers(pack_start, pack_count)
            
            if pack_regs:
                pack_info = self.parser.parse_pack_info(
                    pack_regs, 
                    self.client.u32, 
                    self.client.s32
                )
                if pack_info:
                    self._write(f, f"电池电流        : {pack_info['current']:.2f} A")
                    self._write(f, f"剩余容量        : {pack_info['remaining_capacity']} mAh")
                    self._write(f, f"满充容量        : {pack_info['full_capacity']} mAh")
                    self._write(f, f"充电电流        : {pack_info['charge_current']:.2f} A")
                    self._write(f, f"充电电压        : {pack_info['charge_voltage']:.2f} V")
                    self._write(f, f"PACK 总电压     : {pack_info['pack_voltage']:.2f} V")
                    self._write(f, f"电池电压        : {pack_info['battery_voltage']:.2f} V")
                    self._write(f, f"循环次数        : {pack_info['cycle_count']}")
                    self._write(f, f"剩余可用时间    : {pack_info['time_to_empty']} min")
                    self._write(f, f"充满所需时间    : {pack_info['time_to_full']} min")
                    self._write(f, f"SOC             : {pack_info['soc']} %")
                    self._write(f, f"SOH             : {pack_info['soh']} %")
            
            # 单体电压
            self._write(f, "\n[单体电压]")
            cell_start = reg_cfg.get("cell_voltage_start", 0x0800)
            cell_count = reg_cfg.get("cell_voltage_count", 16)
            cell_regs = self.client.read_registers(cell_start, cell_count)
            
            if cell_regs:
                cell_info = self.parser.parse_cell_voltages(cell_regs)
                if cell_info:
                    self._write(f, f"最高单体电压    : {cell_info['voltage_max']} mV")
                    self._write(f, f"最低单体电压    : {cell_info['voltage_min']} mV")
                    for cell in cell_info['cells']:
                        self._write(f, f"Cell {cell['cell_num']:02d} 电压      : {cell['voltage']} mV")
            
            # 温度信息
            self._write(f, "\n[温度信息]")
            temp_start = reg_cfg.get("temperature_start", 0x0C00)
            temp_count = reg_cfg.get("temperature_count", 4)
            temp_regs = self.client.read_registers(temp_start, temp_count)
            
            if temp_regs:
                temp_info = self.parser.parse_temperatures(temp_regs)
                if temp_info:
                    if temp_info['temp_max'] is not None:
                        self._write(f, f"最高温度        : {temp_info['temp_max']:.1f} ℃")
                    if temp_info['temp_min'] is not None:
                        self._write(f, f"最低温度        : {temp_info['temp_min']:.1f} ℃")
                    for temp in temp_info['temps']:
                        self._write(f, f"温度 {temp['sensor_num']}          : {temp['temperature']:.1f} ℃")
            
            # 状态信息
            self._write(f, "\n[状态信息]")
            status_start = reg_cfg.get("status_start", 0x1000)
            status_count = reg_cfg.get("status_count", 3)
            status_regs = self.client.read_registers(status_start, status_count)
            
            if status_regs:
                status_info = self.parser.parse_status(status_regs)
                if status_info:
                    self._write(f, f"AFE 状态        : 0x{status_info['afe_status']:04X}")
                    self._write(f, f"AFE 安全        : 0x{status_info['afe_safety']:04X}")
                    self._write(f, f"均衡状态        : 0x{status_info['balance']:04X}")
            
            self._write(f, "\n===== 扫描结束 =====")
            self._write(f, f"结果已保存到: {self.output_file}")
        
        self.client.disconnect()


def main():
    """主函数"""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    
    try:
        scanner = BMSScanner(config_path)
        scanner.scan()
    except Exception as e:
        print(f"扫描失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

