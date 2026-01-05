# 版本管理和自动更新指南

本文档介绍如何使用版本管理和自动更新功能。

## 功能概述

- ✅ **版本标识**: 在代码中嵌入版本号和特殊标志
- ✅ **自动版本生成**: 推送代码时自动生成版本信息文件
- ✅ **版本轮询**: 部署机定期检查远程版本
- ✅ **自动更新控制**: 开发机配置是否启用自动更新
- ✅ **标志检测**: 自动判断版本是否包含特定代码或功能

## 工作原理

1. **开发机推送代码时**:
   - 自动生成 `VERSION.json` 文件，包含版本号、构建哈希和特殊标志
   - 版本信息文件提交到Git仓库
   - 创建Git标签并推送到远程

2. **部署机轮询检查**:
   - 定期检查远程Git仓库的最新版本
   - 读取配置文件判断是否启用自动更新
   - 如果启用自动更新且检测到新版本，触发watchtower更新容器

## 配置说明

在 `config/config.yaml` 中配置版本管理：

```yaml
version:
  # 是否启用自动更新（开发机配置，部署机读取此配置决定是否自动更新）
  auto_update_enabled: false  # true: 启用自动更新, false: 禁用自动更新
  # 版本检查间隔（秒），部署机轮询间隔
  check_interval: 300  # 默认5分钟检查一次
  # 版本信息文件路径（相对于项目根目录）
  version_file: "VERSION.json"
  # 特殊标志配置（开发机设置，用于标识特定功能或代码）
  flags:
    # 示例标志，可根据需要添加
    # critical_update: false  # 关键更新标志
    # feature_enabled: true   # 功能启用标志
    # experimental: false     # 实验性功能标志
```

### 配置项说明

- **auto_update_enabled**: 开发机设置的标志，控制部署机是否自动更新
  - `true`: 部署机检测到新版本后自动更新
  - `false`: 部署机只检查但不自动更新，需要手动更新

- **check_interval**: 部署机版本检查的间隔时间（秒）

- **flags**: 特殊标志字典，开发机可以设置任意标志，用于标识版本的特殊属性

## 使用流程

### 开发机操作

#### 1. 设置自动更新开关

编辑 `config/config.yaml`，设置 `auto_update_enabled`:

```yaml
version:
  auto_update_enabled: true  # 启用自动更新
  flags:
    critical_update: true    # 设置特殊标志
```

#### 2. 推送代码

推送代码时会自动生成版本信息文件：

```bash
# 默认递增patch版本
bash scripts/git-push.sh

# 或指定版本类型
bash scripts/git-push.sh minor
bash scripts/git-push.sh major
```

推送时会自动：
- 生成 `VERSION.json` 文件（包含版本号、构建哈希和配置中的flags）
- 提交版本信息文件到Git
- 创建Git标签并推送

### 部署机操作

#### 1. 检查版本更新（单次）

```bash
# 检查是否有新版本
python3 scripts/version_check.py
```

输出JSON格式的检查结果：
```json
{
  "need_update": true,
  "local_version": "v1.0.0",
  "remote_version": "v1.0.1",
  "auto_update_enabled": true,
  "flags": {
    "critical_update": true
  }
}
```

#### 2. 启动版本轮询服务

```bash
# 后台运行轮询服务
nohup bash scripts/version_poll.sh > logs/version_poll.log 2>&1 &

# 或使用systemd服务（推荐）
# 创建服务文件 /etc/systemd/system/battery-version-poll.service
```

轮询服务会：
- 按照配置的间隔定期检查版本
- 如果 `auto_update_enabled=true` 且检测到新版本，自动触发更新
- 如果 `auto_update_enabled=false`，只记录日志，不自动更新

#### 3. 单次检查并更新

```bash
# 单次检查，如果配置允许会自动更新
bash scripts/version_poll.sh --once
```

#### 4. 手动更新

如果自动更新被禁用，可以手动更新：

```bash
# 拉取最新版本
bash scripts/git-pull.sh

# 如果使用Docker，重新构建和启动
docker-compose pull
docker-compose up -d --build
```

## 与Watchtower集成

### 方式1: 使用docker-compose（推荐）

```bash
# 使用watchtower配置启动
docker-compose -f docker-compose.yml -f docker-compose.watchtower.yml up -d
```

watchtower会自动监控容器并更新。

### 方式2: 独立运行watchtower

```bash
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 300 \
  --label-enable
```

### 方式3: 使用版本轮询脚本

版本轮询脚本会自动触发docker-compose更新，无需watchtower。

## 版本信息文件格式

`VERSION.json` 文件格式：

```json
{
  "version": "v1.0.1",
  "build_hash": "a1b2c3d",
  "flags": {
    "critical_update": true,
    "feature_enabled": true
  }
}
```

## 在代码中使用版本信息

```python
from src.version import get_version_info, get_version

# 获取版本号字符串
version = get_version()  # "v1.0.1"

# 获取完整的版本信息对象
version_info = get_version_info()
if version_info:
    print(f"版本: {version_info.version}")
    print(f"构建哈希: {version_info.build_hash}")
    
    # 检查标志
    if version_info.has_flag("critical_update"):
        print("这是关键更新")
    
    # 获取标志值
    feature_enabled = version_info.get_flag("feature_enabled", False)
```

## 最佳实践

1. **开发机配置**:
   - 开发新功能时，设置 `auto_update_enabled: false`，避免自动部署不稳定版本
   - 稳定版本准备发布时，设置 `auto_update_enabled: true`
   - 使用flags标识版本特性（如critical_update, experimental等）

2. **部署机配置**:
   - 生产环境建议使用systemd服务运行轮询脚本
   - 设置合适的检查间隔（避免过于频繁）
   - 监控日志，确保自动更新正常工作

3. **版本管理**:
   - 使用语义化版本号（major.minor.patch）
   - 关键更新使用major版本
   - 新功能使用minor版本
   - Bug修复使用patch版本

## 故障排除

### 版本检查失败

- 检查Git仓库连接是否正常
- 确认远程仓库地址配置正确
- 检查网络连接

### 自动更新不工作

- 检查配置文件中的 `auto_update_enabled` 是否为 `true`
- 检查轮询服务是否正常运行
- 查看日志文件 `logs/version_poll.log`

### Watchtower不更新

- 确认watchtower容器正在运行
- 检查容器标签配置
- 查看watchtower日志: `docker logs watchtower`

