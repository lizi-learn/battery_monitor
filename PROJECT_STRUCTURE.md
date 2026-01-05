# 项目结构说明

## 目录结构

```
battery_test/
├── README.md                 # 项目主文档
├── CHANGELOG.md             # 版本更新日志
├── PROJECT_STRUCTURE.md     # 项目结构说明（本文件）
├── requirements.txt         # Python 依赖包
├── setup.py                 # 安装脚本
├── Dockerfile               # Docker 镜像构建文件
├── docker-compose.yml       # Docker Compose 配置
├── .gitignore              # Git 忽略文件
├── .gitattributes          # Git 属性配置
│
├── config/                 # 配置文件目录
│   └── config.yaml         # 主配置文件（串口、Modbus、日志、阈值等）
│
├── src/                    # 源代码目录
│   ├── __init__.py        # 包初始化文件
│   ├── modbus_client.py   # Modbus RTU 通信客户端
│   ├── bms_parser.py      # BMS 数据解析器
│   ├── bms_monitor.py     # 监测主程序
│   └── bms_scanner.py     # 全参数扫描工具
│
├── scripts/                # 脚本目录
│   ├── deploy.sh          # 系统服务部署脚本
│   ├── scan_bms.sh        # BMS 端口扫描脚本
│   ├── git-push.sh        # Git 推送脚本（开发机）
│   ├── git-pull.sh         # Git 拉取脚本（部署机）
│   ├── git-rollback.sh    # 版本回退脚本
│   ├── git-version.sh     # 版本查看脚本
│   ├── docker-build.sh    # Docker 构建脚本
│   ├── docker-run.sh      # Docker 运行脚本
│   └── docker-quickstart.sh # Docker 快速启动脚本
│
├── docs/                   # 文档目录
│   ├── README.md          # 文档索引
│   ├── DOCKER_DEPLOY.md   # Docker 部署指南
│   ├── GIT_SYNC_GUIDE.md  # Git 同步使用指南
│   ├── QUICK_REFERENCE.md # 快速参考
│   ├── 通信协议.txt       # Modbus 通信协议文档
│   └── pdfs/              # PDF 文档目录
│       └── BMS MODBUS 协议.pdf
│
├── logs/                   # 日志目录（自动创建，git忽略）
│   ├── bms_monitor.log    # 监测日志
│   └── bms_scan.log       # 扫描日志
│
├── tests/                  # 测试目录（预留）
│
└── archive/                # 归档目录（历史文件）
    ├── README.md          # 归档说明
    ├── old_code/          # 旧代码文件
    └── old_output/        # 旧输出文件
```

## 核心模块说明

### 1. modbus_client.py
Modbus RTU 通信客户端模块，提供：
- 串口连接管理
- Modbus 寄存器读取
- CRC16 校验
- 数据类型转换（u32, s32）

### 2. bms_parser.py
BMS 数据解析模块，提供：
- PACK 信息解析
- 单体电压解析
- 温度信息解析
- 状态信息解析
- 告警位解码
- 阈值检查

### 3. bms_monitor.py
监测主程序，功能：
- 持续监测电池状态
- 自动告警检测
- 日志记录和轮转
- 配置文件加载

### 4. bms_scanner.py
全参数扫描工具，功能：
- 扫描所有 BMS 参数
- 格式化输出
- 保存扫描结果

## 配置文件说明

`config/config.yaml` 包含所有可配置项：

- **serial**: 串口配置（端口、波特率等）
- **modbus**: Modbus 配置（设备地址）
- **logging**: 日志配置（目录、文件、大小限制）
- **monitor**: 监测配置（扫描间隔）
- **thresholds**: 安全阈值（电压、温度、SOC）
- **registers**: 寄存器地址映射

## 使用方式

### 开发模式
```bash
# 实时监测
python -m src.bms_monitor

# 全参数扫描
python -m src.bms_scanner
```

### 生产部署
```bash
# 安装为系统服务
sudo bash scripts/deploy.sh --install

# 查看服务状态
sudo systemctl status battrey

# 查看日志
tail -f logs/bms_monitor.log
```

## 版本管理

- 使用 Git 进行版本控制
- 使用语义化版本号（Semantic Versioning）
- 当前版本：v1.0.0
- 远程仓库：git@github.com:lizi-learn/battery_monitor.git

## 依赖包

- pyserial >= 3.5
- PyYAML >= 6.0

## 注意事项

1. 首次使用前需要修改 `config/config.yaml` 中的串口配置
2. 确保有串口设备的访问权限（可能需要将用户添加到 dialout 组）
3. 日志文件会自动轮转，避免占用过多磁盘空间
4. 旧文件（all.py, battery.py, 参考.py 等）已保留但不再使用

