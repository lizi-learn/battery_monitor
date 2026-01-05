"""
BMS 数据解析模块
解析 Modbus 寄存器数据为可读的电池信息
"""

from typing import Optional, Dict, List, Tuple


class BMSParser:
    """BMS 数据解析器"""
    
    # 告警位定义
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
    
    # 安全位定义
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
    
    @staticmethod
    def parse_pack_info(regs: List[int], u32_func, s32_func) -> Optional[Dict]:
        """
        解析 PACK 信息
        
        Args:
            regs: 寄存器值列表（从 0x0400 开始）
            u32_func: 无符号32位转换函数
            s32_func: 有符号32位转换函数
            
        Returns:
            解析后的 PACK 信息字典，失败返回 None
        """
        if not regs or len(regs) < 0x16:
            return None
        
        # 按通信协议解析
        current_ma = s32_func(regs[0], regs[1])  # 0x0400/0x0401
        rem_cap = u32_func(regs[2], regs[3])      # 0x0402/0x0403
        full_cap = u32_func(regs[4], regs[5])    # 0x0404/0x0405
        charge_current = u32_func(regs[6], regs[7])  # 0x0406/0x0407
        charge_voltage = u32_func(regs[8], regs[9])  # 0x0408/0x0409
        pack_voltage = u32_func(regs[10], regs[11])  # 0x040A/0x040B
        batt_voltage = u32_func(regs[12], regs[13])  # 0x040C/0x040D
        cycle = regs[14]  # 0x040E
        t_empty = regs[15]  # 0x040F
        t_full = regs[16]   # 0x0410
        soc = regs[17]      # 0x0411
        soh = regs[18]      # 0x0412
        batt_status = regs[19]  # 0x0413
        batt_alarm = regs[20]   # 0x0414
        batt_safety = regs[21]  # 0x0415
        
        return {
            "current": current_ma / 1000.0,  # A
            "remaining_capacity": rem_cap,  # mAh
            "full_capacity": full_cap,  # mAh
            "charge_current": charge_current / 1000.0,  # A
            "charge_voltage": charge_voltage / 1000.0,  # V
            "pack_voltage": pack_voltage / 1000.0,  # V
            "battery_voltage": batt_voltage / 1000.0,  # V
            "cycle_count": cycle,
            "time_to_empty": t_empty,  # min
            "time_to_full": t_full,  # min
            "soc": soc,  # %
            "soh": soh,  # %
            "battery_status": batt_status,
            "battery_alarm": batt_alarm,
            "battery_safety": batt_safety,
        }
    
    @staticmethod
    def parse_cell_voltages(regs: List[int]) -> Optional[Dict]:
        """
        解析单体电压信息
        
        Args:
            regs: 寄存器值列表（从 0x0800 开始）
            
        Returns:
            解析后的单体电压信息字典
        """
        if not regs or len(regs) < 2:
            return None
        
        result = {
            "voltage_max": regs[0],  # 0x0800
            "voltage_min": regs[1],  # 0x0801
            "cells": []
        }
        
        # 解析各单体电压（从 0x0802 开始）
        for i in range(2, min(len(regs), 16)):
            if i < len(regs):
                result["cells"].append({
                    "cell_num": i - 1,
                    "voltage": regs[i]  # mV
                })
        
        return result
    
    @staticmethod
    def parse_temperatures(regs: List[int]) -> Optional[Dict]:
        """
        解析温度信息
        
        Args:
            regs: 寄存器值列表（从 0x0C00 开始）
            
        Returns:
            解析后的温度信息字典
        """
        if not regs or len(regs) < 1:
            return None
        
        result = {
            "temp_max": (regs[0] - 2731) / 10.0 if len(regs) > 0 else None,  # 0x0C00
            "temp_min": (regs[1] - 2731) / 10.0 if len(regs) > 1 else None,  # 0x0C01
            "temps": []
        }
        
        # 解析各温度传感器（从 0x0C02 开始）
        for i in range(2, min(len(regs), 6)):
            if i < len(regs):
                temp_c = (regs[i] - 2731) / 10.0
                result["temps"].append({
                    "sensor_num": i - 2,
                    "temperature": temp_c  # ℃
                })
        
        return result
    
    @staticmethod
    def parse_status(regs: List[int]) -> Optional[Dict]:
        """
        解析状态信息
        
        Args:
            regs: 寄存器值列表（从 0x1000 开始）
            
        Returns:
            解析后的状态信息字典
        """
        if not regs or len(regs) < 3:
            return None
        
        return {
            "afe_status": regs[0],   # 0x1000
            "afe_safety": regs[1],    # 0x1001
            "balance": regs[2],       # 0x1002
        }
    
    @classmethod
    def decode_alarm(cls, val: int) -> List[str]:
        """
        解码告警位
        
        Args:
            val: 告警寄存器值
            
        Returns:
            告警信息列表
        """
        if val == 0:
            return []
        return cls._decode_bits(val, cls.BATTERY_ALARM_BITS)
    
    @classmethod
    def decode_safety(cls, val: int) -> List[str]:
        """
        解码安全位
        
        Args:
            val: 安全寄存器值
            
        Returns:
            安全信息列表
        """
        if val == 0:
            return []
        return cls._decode_bits(val, cls.BATTERY_SAFETY_BITS)
    
    @staticmethod
    def _decode_bits(val: int, bit_map: Dict[int, str]) -> List[str]:
        """
        解码位标志
        
        Args:
            val: 寄存器值
            bit_map: 位映射字典
            
        Returns:
            解码后的信息列表
        """
        msgs = []
        for bit, desc in bit_map.items():
            if val & (1 << bit):
                msgs.append(desc)
        return msgs
    
    @staticmethod
    def check_thresholds(pack_v: float, current_a: float, soc: int, 
                        tmax_c: float, thresholds: Dict) -> List[str]:
        """
        检查阈值告警
        
        Args:
            pack_v: PACK 电压（V）
            current_a: 电流（A）
            soc: SOC（%）
            tmax_c: 最高温度（℃）
            thresholds: 阈值配置字典
            
        Returns:
            告警信息列表
        """
        alarms = []
        
        pack_v_th = thresholds.get("pack_voltage", {})
        if pack_v > pack_v_th.get("max", 58.4):
            alarms.append("PACK 电压过高")
        if pack_v < pack_v_th.get("min", 40.0):
            alarms.append("PACK 电压过低")
        
        temp_th = thresholds.get("temperature", {})
        if tmax_c > temp_th.get("max", 60.0):
            alarms.append("最高温度过高")
        if tmax_c < temp_th.get("min", 0.0):
            alarms.append("环境过低温")
        
        soc_th = thresholds.get("soc", {})
        if soc >= soc_th.get("high", 100):
            alarms.append("电量已满")
        if soc <= soc_th.get("low", 5):
            alarms.append("电量过低")
        
        return alarms

