# Git 多端同步使用指南

本指南介绍如何使用 Git 同步脚本在多端设备间快速同步代码，并管理版本。

## 脚本说明

### 1. git-push.sh - 开发机推送脚本

**功能：**
- 自动检测当前版本并递增版本号
- 提交并推送代码到远程仓库
- 创建并推送版本标签

**使用方法：**

```bash
# 默认递增 patch 版本 (v1.0.0 -> v1.0.1)
bash scripts/git-push.sh

# 递增 minor 版本 (v1.0.0 -> v1.1.0)
bash scripts/git-push.sh minor

# 递增 major 版本 (v1.0.0 -> v2.0.0)
bash scripts/git-push.sh major

# 指定提交信息
bash scripts/git-push.sh patch "修复了某个bug"
```

**版本号规则：**
- `patch`: 补丁版本，修复bug或小改动 (1.0.0 -> 1.0.1)
- `minor`: 次版本，新功能或较大改动 (1.0.0 -> 1.1.0)
- `major`: 主版本，重大变更或不兼容更新 (1.0.0 -> 2.0.0)

### 2. git-pull.sh - 部署机拉取脚本

**功能：**
- 显示当前版本和远程最新版本
- 显示版本变更日志
- 拉取并切换到指定版本

**使用方法：**

```bash
# 拉取最新版本
bash scripts/git-pull.sh

# 拉取指定版本
bash scripts/git-pull.sh v1.0.2
```

**输出示例：**
```
[VERSION] 当前本地版本: v1.0.0
[VERSION] 远程最新版本: v1.0.2

[INFO] 版本变更信息:
  v1.0.0 -> v1.0.2
[INFO] 变更内容:
  - feat: 添加新功能
  - fix: 修复bug

是否继续拉取版本 v1.0.2? (y/N):
```

### 3. git-rollback.sh - 版本回退脚本

**功能：**
- 快速回退到上一个版本
- 自动保存版本信息用于回退

**使用方法：**

```bash
bash scripts/git-rollback.sh
```

**输出示例：**
```
[VERSION] 当前版本: v1.0.2
[VERSION] 上一个版本: v1.0.1

[INFO] 版本回退信息:
  当前版本: v1.0.2
  回退到: v1.0.1

确认回退到版本 v1.0.1? (y/N):
```

### 4. git-version.sh - 版本查看脚本

**功能：**
- 查看当前本地版本
- 查看远程最新版本
- 列出所有可用版本

**使用方法：**

```bash
bash scripts/git-version.sh
```

**输出示例：**
```
[VERSION] 本地当前版本: v1.0.1
[VERSION] 上一个版本: v1.0.0
[VERSION] 远程最新版本: v1.0.2

[INFO] 所有可用版本:
    v1.0.0
  → v1.0.1 (当前)
    v1.0.2
```

## 典型工作流程

### 开发机（推送代码）

```bash
# 1. 修改代码后，推送并创建新版本
bash scripts/git-push.sh patch "添加了新的监测功能"

# 输出：
# [INFO] 当前版本: v1.0.0
# [INFO] 新版本: v1.0.1
# [SUCCESS] 推送完成！
# [SUCCESS] 版本: v1.0.0 -> v1.0.1
```

### 部署机（拉取代码）

```bash
# 1. 查看当前版本
bash scripts/git-version.sh

# 2. 拉取最新版本
bash scripts/git-pull.sh

# 3. 如果新版本有问题，快速回退
bash scripts/git-rollback.sh
```

## 版本管理机制

### 版本文件

脚本会自动创建以下文件来追踪版本：

- `.git_current_version`: 当前版本号
- `.git_previous_version`: 上一个版本号（用于回退）

这些文件会被提交到 Git，以便在多端设备间同步版本信息。

### 版本标签

每个版本都会创建一个 Git 标签，格式为 `v主版本.次版本.补丁版本`，例如：
- `v1.0.0`
- `v1.0.1`
- `v1.1.0`
- `v2.0.0`

### 版本回退机制

1. **自动保存**: `git-pull.sh` 会自动保存当前版本到 `.git_previous_version`
2. **快速回退**: `git-rollback.sh` 读取保存的版本信息并回退
3. **安全确认**: 所有版本切换操作都需要用户确认

## 注意事项

1. **首次使用**: 确保已配置 SSH 密钥或 HTTPS 认证
2. **网络连接**: 拉取和推送需要网络连接
3. **版本冲突**: 如果本地有未提交的更改，需要先提交或暂存
4. **权限问题**: 确保有远程仓库的推送权限

## 故障排查

### 问题：无法连接到远程仓库

```bash
# 检查远程仓库配置
git remote -v

# 测试连接
ssh -T git@github.com
```

### 问题：版本标签不存在

```bash
# 获取所有远程标签
git fetch origin --tags

# 查看所有版本
bash scripts/git-version.sh
```

### 问题：回退失败

```bash
# 手动查看版本历史
git tag -l

# 手动切换到指定版本
git checkout v1.0.0
```

## 高级用法

### 查看版本间的差异

```bash
# 查看两个版本间的代码差异
git diff v1.0.0 v1.0.1

# 查看版本间的提交日志
git log v1.0.0..v1.0.1 --oneline
```

### 批量操作

```bash
# 在多个部署机上批量拉取
for host in deploy1 deploy2 deploy3; do
    ssh $host "cd /path/to/project && bash scripts/git-pull.sh"
done
```

## 最佳实践

1. **版本号使用**: 
   - 小改动用 `patch`
   - 新功能用 `minor`
   - 重大变更用 `major`

2. **提交信息**: 使用清晰的提交信息，便于追踪变更

3. **测试验证**: 在部署机上拉取后，先测试再正式使用

4. **版本记录**: 重要版本变更建议在 CHANGELOG.md 中记录

5. **备份**: 重要版本建议创建备份分支

