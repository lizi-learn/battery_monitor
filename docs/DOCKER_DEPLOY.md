# Docker 部署指南

本指南介绍如何使用 Docker 部署 BMS 监测系统，并确保能够访问串口设备。

## 前置要求

1. **安装 Docker**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   
   # 启动 Docker 服务
   sudo systemctl start docker
   sudo systemctl enable docker
   
   # 将当前用户添加到 docker 组（可选，避免每次使用 sudo）
   sudo usermod -aG docker $USER
   # 需要重新登录生效
   ```

2. **确认串口设备**
   ```bash
   # 查看可用的串口设备
   ls -la /dev/tty*USB*
   
   # 常见设备名称:
   # /dev/ttyUSB0
   # /dev/ttyCH341USB0
   # /dev/ttyACM0
   ```

3. **检查设备权限**
   ```bash
   # 查看设备权限
   ls -l /dev/ttyCH341USB0
   
   # 如果需要，将用户添加到 dialout 组
   sudo usermod -aG dialout $USER
   ```

## 部署方式

### 方式一：使用 docker-compose（推荐）

#### 1. 修改配置

编辑 `docker-compose.yml`，根据实际情况修改串口设备路径：

```yaml
devices:
  - /dev/ttyCH341USB0:/dev/ttyCH341USB0  # 修改为你的设备路径
```

#### 2. 构建并启动

```bash
# 构建镜像
docker-compose build

# 启动服务（后台运行）
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 3. 运行扫描工具

```bash
# 使用 profile 启动扫描服务
docker-compose --profile scanner up bms-scanner
```

### 方式二：直接使用 docker run

#### 1. 构建镜像

```bash
bash scripts/docker-build.sh
```

或手动构建：

```bash
docker build -t bms-monitor:latest .
```

#### 2. 运行容器

```bash
# 使用脚本（推荐）
bash scripts/docker-run.sh /dev/ttyCH341USB0

# 或手动运行
docker run -d \
  --name bms-monitor \
  --restart unless-stopped \
  --device=/dev/ttyCH341USB0:/dev/ttyCH341USB0 \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  bms-monitor:latest
```

## 串口设备映射

Docker 容器访问串口设备有几种方式：

### 方式1: 使用 --device（推荐）

```yaml
devices:
  - /dev/ttyCH341USB0:/dev/ttyCH341USB0
```

**优点：**
- 安全性高，只映射指定设备
- 性能好
- 推荐用于生产环境

### 方式2: 映射多个设备

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0
  - /dev/ttyUSB1:/dev/ttyUSB1
  - /dev/ttyCH341USB0:/dev/ttyCH341USB0
```

### 方式3: 使用 privileged 模式（不推荐）

```yaml
privileged: true
```

**注意：** 这种方式会给予容器所有权限，安全性较低，仅在必要时使用。

## 配置文件管理

### 方式1: 挂载配置文件（推荐）

```yaml
volumes:
  - ./config:/app/config:ro  # 只读挂载
```

这样可以在宿主机修改配置文件，容器会自动使用新配置（需要重启容器）。

### 方式2: 构建到镜像中

修改 Dockerfile，将配置文件复制到镜像：

```dockerfile
COPY config/ ./config/
```

**注意：** 这种方式需要重新构建镜像才能更新配置。

## 日志管理

日志文件会自动挂载到宿主机的 `./logs` 目录：

```yaml
volumes:
  - ./logs:/app/logs
```

查看日志：

```bash
# 容器日志
docker logs -f bms-monitor

# 应用日志文件
tail -f logs/bms_monitor.log
```

## 常用命令

### 查看容器状态

```bash
docker ps | grep bms-monitor
```

### 查看日志

```bash
# 实时日志
docker logs -f bms-monitor

# 最近 100 行
docker logs --tail 100 bms-monitor
```

### 进入容器

```bash
docker exec -it bms-monitor /bin/bash
```

### 停止和删除

```bash
# 停止容器
docker stop bms-monitor

# 删除容器
docker rm bms-monitor

# 使用 docker-compose
docker-compose down
```

### 更新镜像

```bash
# 重新构建
docker-compose build

# 重启服务
docker-compose up -d
```

## 故障排查

### 问题1: 无法访问串口设备

**错误信息：**
```
连接串口失败: [Errno 2] No such file or directory: '/dev/ttyCH341USB0'
```

**解决方法：**

1. 检查设备是否存在：
   ```bash
   ls -la /dev/ttyCH341USB0
   ```

2. 检查 docker-compose.yml 中的设备路径是否正确

3. 检查设备权限：
   ```bash
   ls -l /dev/ttyCH341USB0
   # 应该显示: crw-rw---- 1 root dialout ...
   ```

4. 如果设备名称不同，修改配置文件：
   ```bash
   # 在宿主机上查找设备
   ls -la /dev/tty*USB*
   
   # 修改 docker-compose.yml 和 config/config.yaml
   ```

### 问题2: 权限 denied

**错误信息：**
```
连接串口失败: [Errno 13] Permission denied: '/dev/ttyCH341USB0'
```

**解决方法：**

1. 将用户添加到 dialout 组：
   ```bash
   sudo usermod -aG dialout $USER
   # 重新登录
   ```

2. 或者使用 privileged 模式（不推荐）：
   ```yaml
   privileged: true
   ```

### 问题3: 设备路径在容器中不同

如果宿主机和容器中的设备路径不同，可以在配置文件中使用环境变量：

```yaml
environment:
  - SERIAL_PORT=/dev/ttyUSB0
```

然后修改代码读取环境变量（需要代码支持）。

### 问题4: 容器无法启动

检查日志：

```bash
docker logs bms-monitor
```

常见原因：
- 配置文件错误
- 依赖包缺失
- 端口冲突

## 性能优化

### 1. 使用多阶段构建（可选）

可以优化 Dockerfile 使用多阶段构建，减小镜像大小。

### 2. 资源限制

在 docker-compose.yml 中添加资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
    reservations:
      cpus: '0.25'
      memory: 128M
```

## 安全建议

1. **不要使用 privileged 模式**，除非绝对必要
2. **配置文件使用只读挂载** (`:ro`)
3. **定期更新基础镜像**
4. **限制容器资源使用**
5. **使用非 root 用户运行**（可以在 Dockerfile 中添加）

## 示例：完整部署流程

```bash
# 1. 克隆项目
git clone <repository-url>
cd battery_test

# 2. 检查串口设备
ls -la /dev/tty*USB*

# 3. 修改配置文件
vim config/config.yaml  # 设置正确的串口路径
vim docker-compose.yml  # 确认设备映射

# 4. 构建并启动
docker-compose build
docker-compose up -d

# 5. 查看日志
docker-compose logs -f

# 6. 检查运行状态
docker ps | grep bms-monitor
tail -f logs/bms_monitor.log
```

## 与 systemd 服务对比

| 特性 | Docker | systemd |
|------|--------|---------|
| 隔离性 | ✅ 高 | ❌ 低 |
| 资源管理 | ✅ 好 | ⚠️ 一般 |
| 部署便捷性 | ✅ 高 | ⚠️ 需要脚本 |
| 配置管理 | ✅ 灵活 | ⚠️ 需要修改脚本 |
| 性能开销 | ⚠️ 略高 | ✅ 低 |
| 串口访问 | ⚠️ 需要映射 | ✅ 直接访问 |

选择建议：
- **Docker**: 适合需要隔离、多环境部署的场景
- **systemd**: 适合单机部署、对性能要求高的场景

