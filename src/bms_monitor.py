"""
BMS 电池安全监测主程序
持续监测电池状态并记录日志
"""

import os
import time
import yaml
from typing import Optional
from pathlib import Path

from .modbus_client import ModbusClient
from .bms_parser import BMSParser


class BMSMonitor:
    """BMS 监测器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化监测器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        self.client: Optional[ModbusClient] = None
        self.parser = BMSParser()
        self.log_path = self._get_log_path()
        self._init_log_file()
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _get_log_path(self) -> str:
        """获取日志文件路径"""
        log_dir = self.config.get("logging", {}).get("log_dir", "logs")
        log_file = self.config.get("logging", {}).get("log_file", "bms_monitor.log")
        
        # 确保日志目录存在
        os.makedirs(log_dir, exist_ok=True)
        
        return os.path.join(log_dir, log_file)
    
    def _init_log_file(self):
        """初始化日志文件"""
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', encoding='utf-8') as f:
                f.write("===== BMS 电池安全监测日志 =====\n")
    
    def _append_log(self, line: str):
        """追加日志"""
        max_size = self.config.get("logging", {}).get("max_log_size", 204800)
        rotation = self.config.get("logging", {}).get("log_rotation", True)
        
        try:
            # 日志轮转
            if rotation and os.path.exists(self.log_path):
                if os.path.getsize(self.log_path) > max_size:
                    with open(self.log_path, 'r', encoding='utf-8') as f:
                        data = f.read()
                    keep = data[-(max_size // 2):]
                    with open(self.log_path, 'w', encoding='utf-8') as f:
                        f.write(keep)
            
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(line + "\n")
        except OSError:
            pass  # 日志写入失败不影响主程序
    
    def _read_status(self) -> Optional[dict]:
        """读取一次状态"""
        serial_cfg = self.config.get("serial", {})
        modbus_cfg = self.config.get("modbus", {})
        reg_cfg = self.config.get("registers", {})
        
        if not self.client:
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
                return None
        
        # 读取 PACK 信息
        pack_start = reg_cfg.get("pack_info_start", 0x0400)
        pack_count = reg_cfg.get("pack_info_count", 0x16)
        pack_regs = self.client.read_registers(pack_start, pack_count)
        if not pack_regs:
            return None
        
        pack_info = self.parser.parse_pack_info(
            pack_regs, 
            self.client.u32, 
            self.client.s32
        )
        if not pack_info:
            return None
        
        # 读取最高温度
        temp_start = reg_cfg.get("temperature_start", 0x0C00)
        temp_regs = self.client.read_registers(temp_start, 1)
        if not temp_regs:
            return None
        
        tmax_c = (temp_regs[0] - 2731) / 10.0
        
        return {
            "pack_voltage": pack_info["pack_voltage"],
            "current": pack_info["current"],
            "soc": pack_info["soc"],
            "tmax": tmax_c,
            "batt_alarm": pack_info["battery_alarm"],
            "batt_safety": pack_info["battery_safety"],
        }
    
    def run(self):
        """运行监测循环"""
        print("🔋 BMS 安全监测已启动，按 Ctrl+C 退出。\n")
        
        try:
            scan_interval = self.config.get("monitor", {}).get("scan_interval", 5)
            thresholds = self.config.get("thresholds", {})
            
            while True:
                status = self._read_status()
                if status is None:
                    print("读取 BMS 数据失败，检查连接与地址/波特率设置。")
                    time.sleep(1)
                    continue
                
                pack_v = status["pack_voltage"]
                current_a = status["current"]
                soc = status["soc"]
                tmax_c = status["tmax"]
                batt_alarm = status["batt_alarm"]
                batt_safety = status["batt_safety"]
                
                # 阈值告警
                alarms = self.parser.check_thresholds(
                    pack_v, current_a, soc, tmax_c, thresholds
                )
                
                # 协议告警
                alarms.extend(self.parser.decode_alarm(batt_alarm))
                alarms.extend(self.parser.decode_safety(batt_safety))
                
                # 电流方向
                if current_a > 0:
                    cur_mode = "充电"
                elif current_a < 0:
                    cur_mode = "放电"
                else:
                    cur_mode = "静止"
                cur_abs = abs(current_a)
                
                # 格式化输出
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
                self._append_log(line)
                
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            print("\n退出监测。")
        finally:
            if self.client:
                self.client.disconnect()


def main():
    """主函数"""
    import sys
    
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/config.yaml"
    
    try:
        monitor = BMSMonitor(config_path)
        monitor.run()
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

