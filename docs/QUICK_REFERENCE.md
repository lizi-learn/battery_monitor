# Git 同步脚本快速参考

## 开发机（推送）

```bash
# 推送并创建新版本（patch: 1.0.0 -> 1.0.1）
bash scripts/git-push.sh

# 推送并创建 minor 版本（1.0.0 -> 1.1.0）
bash scripts/git-push.sh minor

# 推送并创建 major 版本（1.0.0 -> 2.0.0）
bash scripts/git-push.sh major
```

## 部署机（拉取）

```bash
# 查看版本
bash scripts/git-version.sh

# 拉取最新版本
bash scripts/git-pull.sh

# 拉取指定版本
bash scripts/git-pull.sh v1.0.2

# 回退到上一个版本
bash scripts/git-rollback.sh
```

## 版本号规则

- **patch** (默认): 修复bug，小改动 → 1.0.0 → 1.0.1
- **minor**: 新功能，较大改动 → 1.0.0 → 1.1.0  
- **major**: 重大变更，不兼容 → 1.0.0 → 2.0.0

## 工作流程

```
开发机: 修改代码 → git-push.sh → 远程仓库
                                    ↓
部署机: git-pull.sh ← 远程仓库 ← 版本标签
         ↓
    有问题？→ git-rollback.sh
```

