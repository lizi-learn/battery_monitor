# 更新日志

所有重要的项目变更都会记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2024-12-18

### 新增
- ✨ 实现 BMS 实时监测功能
  - 持续监测电池电压、电流、SOC、温度等关键参数
  - 自动检测异常并告警
  - 支持日志记录和轮转
  
- ✨ 实现 BMS 全参数扫描功能
  - 扫描并输出所有 BMS 参数
  - 包括 PACK 信息、单体电压、温度、状态等
  
- ✨ 模块化代码结构
  - `modbus_client.py`: Modbus RTU 通信客户端
  - `bms_parser.py`: BMS 数据解析器
  - `bms_monitor.py`: 监测主程序
  - `bms_scanner.py`: 扫描工具
  
- ✨ 配置文件化管理
  - 使用 YAML 格式配置文件
  - 所有参数可通过配置文件修改
  - 支持串口、Modbus、日志、阈值等配置
  
- ✨ 项目标准化
  - 标准项目目录结构
  - requirements.txt 依赖管理
  - setup.py 安装脚本
  - README.md 完整文档
  - .gitignore 文件
  
- ✨ 部署脚本
  - systemd 服务部署脚本
  - Git 推送脚本
  - BMS 扫描脚本

### 变更
- 🔄 重构项目结构，从单文件脚本改为模块化项目
- 🔄 将硬编码配置提取到配置文件

### 技术栈
- Python 3.6+
- pyserial: Modbus 串口通信
- PyYAML: 配置文件解析

