# test_all — BMS 与系统温度

## 持续监测（推荐）

持续显示：**电池百分比、是否充电、电池温度** + **CPU、NVMe 温度**，便于监控与传数据。

```bash
python3 test_all.py --monitor
```

按 **Ctrl+C** 退出。

示例输出：

```
持续监测温度（电池 + CPU + NVMe），按 Ctrl+C 退出

[13:30:23] 电池 40% 放电中 26~33℃ | CPU 44.0℃ | NVMe 36.9℃
[13:30:25] 电池 40% 放电中 26~33℃ | CPU 40.0℃ | NVMe 36.9℃
```

- **电池**：SOC%、充电中/放电中/静置、温度范围（℃）
- **CPU / NVMe**：电脑温度（依赖 `sensors`，见下方依赖）

---

## 依赖

```bash
pip install -r requirements.txt
```

或：`pip install pyserial`

- 电池数据：BMS 接串口（默认 `/dev/ttyCH341USB1`，可在脚本内改 `PORT`）。
- 电脑温度：系统需安装 `lm-sensors`，命令行可用 `sensors`。

---

## 一次性全参数扫描

不加重启参数时，运行一次扫描并写入 `test_all.txt`：

```bash
python3 test_all.py
```

输出内容：设备 ID、PACK 信息（电流/容量/电压/SOC/SOH/状态等）、单体电压、温度、状态（均为中文，无 16 进制）。
