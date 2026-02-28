#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
持续监测电脑温度（CPU、NVMe），超阈值写日志并告警。
可单独运行，也可被 test_all.py 导入用于合并显示。
依赖: 系统已安装 lm-sensors，命令行有 sensors
"""

import re
import subprocess
import time
from pathlib import Path

# ========= 配置 =========
CPU_WARN = 85
NVME_WARN = 75
LOG_FILE = Path.home() / "temp_monitor.log"
INTERVAL = 2
# =========================


def get_cpu_temp():
    """从 sensors 解析 CPU Package 温度，返回 float(℃) 或 None"""
    try:
        out = subprocess.check_output(["sensors"], text=True, timeout=5)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    for line in out.splitlines():
        if "Package id 0" in line or "Core 0" in line:
            m = re.search(r"\+(\d+\.?\d*)\s*°?C", line)
            if m:
                return float(m.group(1))
    return None


def get_nvme_temp():
    """从 sensors 解析 NVMe Composite 温度，返回 float(℃) 或 None"""
    try:
        out = subprocess.check_output(["sensors"], text=True, timeout=5)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    lines = out.splitlines()
    in_nvme = False
    for line in lines:
        if "nvme" in line.lower() and "pci" in line.lower():
            in_nvme = True
            continue
        if in_nvme and "Composite" in line:
            m = re.search(r"\+(\d+\.?\d*)\s*°?C", line)
            if m:
                return float(m.group(1))
            in_nvme = False
    return None


def log_msg(msg: str):
    t = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{t} | {msg}\n")


def run_standalone():
    """独立运行：仅监测电脑温度，循环打印并写日志"""
    print("Starting temperature monitor (CPU + NVMe)...")
    log_msg("Temperature monitor started.")
    while True:
        cpu = get_cpu_temp()
        nvme = get_nvme_temp()
        cpu_s = f"{cpu:.1f}" if cpu is not None else "—"
        nvme_s = f"{nvme:.1f}" if nvme is not None else "—"
        print(f"CPU: {cpu_s}°C | NVMe: {nvme_s}°C")
        if cpu is not None and cpu > CPU_WARN:
            log_msg(f"WARNING: CPU Overheat {cpu:.1f}°C")
            print("⚠ CPU Overheat!")
        if nvme is not None and nvme > NVME_WARN:
            log_msg(f"WARNING: NVMe Overheat {nvme:.1f}°C")
            print("⚠ NVMe Overheat!")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    run_standalone()
