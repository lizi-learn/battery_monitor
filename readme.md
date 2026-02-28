# test_all — BMS 全参数扫描

通过串口 Modbus 读取 BMS 实际数据，输出为人可读的文本（无 16 进制），便于查看或传到别处。

## 依赖

```bash
pip install -r requirements.txt
```

或：

```bash
pip install pyserial
```

## 使用

1. 将 BMS 接到电脑串口（默认 `/dev/ttyCH341USB1`，可在脚本内改 `PORT`）。
2. 运行：

```bash
python3 test_all.py
```

结果会打印到终端，并写入同目录下的 `test_all.txt`。

## 输出内容

- **设备**：设备 ID（ASCII）
- **PACK 信息**：电流、容量、电压、SOC/SOH、循环次数、剩余/充满时间、电池状态/告警/保护（中文说明）
- **单体电压**：最高/最低、各节电压（未接入显示为 —）
- **温度**：MAX/MIN/Temp1/Temp2（℃）
- **状态**：运行（充电MOS、放电、充电中等）、保护、均衡（未均衡/均衡中）

所有状态位已解码为中文，无原始 16 进制。
