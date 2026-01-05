# BMS 电池管理系统监测工具

一个基于 Modbus RTU 协议的 BMS（电池管理系统）监测工具，支持实时监测电池状态、全参数扫描和日志记录。

## 功能特性

- ✅ **实时监测**：持续监测电池电压、电流、SOC、温度等关键参数
- ✅ **全参数扫描**：扫描并输出所有 BMS 参数
- ✅ **安全告警**：自动检测电压、温度、SOC 异常并告警
- ✅ **日志记录**：自动记录监测数据，支持日志轮转
- ✅ **配置化**：所有参数通过配置文件管理
- ✅ **模块化设计**：代码结构清晰，易于维护和扩展

## 项目结构

```
battery_test/
├── README.md              # 项目说明文档
├── requirements.txt      # Python 依赖
├── .gitignore            # Git 忽略文件
├── config/               # 配置文件目录
│   └── config.yaml       # 主配置文件
├── src/                  # 源代码目录
│   ├── __init__.py
│   ├── modbus_client.py  # Modbus 通信客户端
│   ├── bms_parser.py     # BMS 数据解析器
│   ├── bms_monitor.py    # 监测主程序
│   └── bms_scanner.py    # 扫描工具
├── scripts/              # 脚本目录
│   ├── deploy.sh         # 部署脚本
│   ├── scan_bms.sh       # BMS 扫描脚本
│   ├── git-push.sh       # Git 推送脚本（开发机）
│   ├── git-pull.sh       # Git 拉取脚本（部署机）
│   ├── git-rollback.sh   # 版本回退脚本
│   └── git-version.sh    # 版本查看脚本
├── logs/                 # 日志目录
│   ├── bms_monitor.log   # 监测日志
│   └── bms_scan.log      # 扫描日志
└── docs/                 # 文档目录
    └── 通信协议.txt      # Modbus 通信协议文档
```

## 安装

### 1. 克隆仓库

```bash
git clone <repository-url>
cd battery_test
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

编辑 `config/config.yaml` 文件，根据实际情况修改串口配置：

```yaml
serial:
  port: "/dev/ttyCH341USB0"  # 修改为你的串口设备
  baudrate: 9600
  # ...
```

## 使用方法

### 实时监测

运行监测程序，持续监测电池状态：

```bash
python -m src.bms_monitor
```

或指定配置文件：

```bash
python -m src.bms_monitor config/config.yaml
```

### 全参数扫描

扫描并输出所有 BMS 参数：

```bash
python -m src.bms_scanner
```

或指定配置文件：

```bash
python -m src.bms_scanner config/config.yaml
```

### 系统服务部署

使用部署脚本安装为 systemd 服务：

```bash
sudo bash scripts/deploy.sh --install
```

查看服务状态：

```bash
sudo systemctl status battrey
```

查看日志：

```bash
tail -f logs/bms_monitor.log
```

卸载服务：

```bash
sudo bash scripts/deploy.sh --uninstall
```

### 多端代码同步

项目提供了完整的 Git 同步脚本，支持版本管理和快速部署：

#### 开发机（推送代码）

```bash
# 推送代码并自动创建版本标签（默认递增 patch 版本）
bash scripts/git-push.sh

# 递增 minor 版本
bash scripts/git-push.sh minor

# 递增 major 版本
bash scripts/git-push.sh major

# 指定提交信息
bash scripts/git-push.sh patch "修复了某个bug"
```

#### 部署机（拉取代码）

```bash
# 查看当前版本
bash scripts/git-version.sh

# 拉取最新版本（会显示版本变更信息）
bash scripts/git-pull.sh

# 拉取指定版本
bash scripts/git-pull.sh v1.0.2

# 如果新版本有问题，快速回退到上一个版本
bash scripts/git-rollback.sh
```

**版本管理特性：**
- ✅ 自动版本号递增（major/minor/patch）
- ✅ 拉取前显示当前版本
- ✅ 拉取后显示新版本和变更日志
- ✅ 支持快速回退到上一个版本
- ✅ 版本信息自动保存和同步

详细使用说明请参考：[Git 多端同步使用指南](docs/GIT_SYNC_GUIDE.md)

## 配置说明

主要配置项在 `config/config.yaml` 中：

- **serial**: 串口配置（端口、波特率等）
- **modbus**: Modbus 配置（设备地址）
- **logging**: 日志配置（日志目录、文件大小限制等）
- **monitor**: 监测配置（扫描间隔）
- **thresholds**: 安全阈值配置（电压、温度、SOC 阈值）
- **registers**: 寄存器地址映射

## 版本管理

项目使用 Git 进行版本管理，当前版本：**v1.0.0**

查看版本标签：

```bash
git tag
```

## 开发

### 代码结构

- `modbus_client.py`: Modbus RTU 通信实现
- `bms_parser.py`: BMS 数据解析和告警检测
- `bms_monitor.py`: 监测主程序
- `bms_scanner.py`: 扫描工具

### 扩展开发

1. 添加新的监测参数：在 `bms_parser.py` 中添加解析逻辑
2. 修改告警规则：在 `config.yaml` 中调整阈值，或在 `bms_parser.py` 中修改检测逻辑
3. 添加新功能：创建新的模块文件，遵循现有代码风格

## 许可证

本项目仅供学习和研究使用。

## 作者

BMS Monitor Team

## 更新日志

### v1.0.0 (2024-12-18)
- 初始版本发布
- 实现实时监测功能
- 实现全参数扫描功能
- 配置文件化管理
- 模块化代码结构

