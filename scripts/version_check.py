#!/usr/bin/env python3
"""
版本检查脚本
部署机使用，检查远程版本并判断是否需要更新
"""

import json
import subprocess
import sys
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False


def get_local_version() -> Optional[str]:
    """获取本地版本号"""
    # 先尝试从VERSION.json读取
    version_file = Path("VERSION.json")
    if version_file.exists():
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('version')
        except Exception:
            pass
    
    # 尝试从git标签读取
    try:
        result = subprocess.run(
            ['git', 'describe', '--tags', '--abbrev=0'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_remote_version() -> Optional[str]:
    """获取远程最新版本号"""
    try:
        # 获取远程标签
        subprocess.run(
            ['git', 'fetch', 'origin', '--tags'],
            capture_output=True,
            check=True
        )
        
        result = subprocess.run(
            ['git', 'ls-remote', '--tags', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 提取版本标签并排序
        versions = []
        for line in result.stdout.split('\n'):
            if 'refs/tags/v' in line:
                tag = line.split('refs/tags/')[-1].strip()
                if tag and tag.startswith('v') and len(tag.split('.')) == 3:
                    versions.append(tag)
        
        if versions:
            # 简单版本排序（按字符串排序通常可以工作）
            versions.sort(key=lambda x: [int(i) for i in x[1:].split('.')])
            return versions[-1]
        
        return None
    except Exception:
        return None


def get_remote_version_info(version: str) -> Optional[Dict[str, Any]]:
    """从远程仓库获取版本信息（从VERSION.json文件）"""
    try:
        # 方法1: 尝试从GitHub raw获取（如果是GitHub仓库）
        repo_url = None
        try:
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip()
            # 如果是GitHub SSH格式，转换为HTTPS
            if 'github.com' in remote_url:
                if remote_url.startswith('git@'):
                    repo_path = remote_url.split(':')[1].replace('.git', '')
                    repo_url = f"https://raw.githubusercontent.com/{repo_path}"
        except Exception:
            pass
        
        if repo_url and HAS_URLLIB:
            version_url = f"{repo_url}/{version}/VERSION.json"
            try:
                with urllib.request.urlopen(version_url, timeout=5) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    return data
            except Exception:
                pass
        
        # 方法2: 从本地git checkout到指定版本后读取（如果标签已存在）
        try:
            # 检查标签是否存在
            result = subprocess.run(
                ['git', 'rev-parse', version],
                capture_output=True,
                check=True
            )
            # 切换到该版本（使用git show读取文件内容，不改变工作目录）
            result = subprocess.run(
                ['git', 'show', f"{version}:VERSION.json"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            return data
        except Exception:
            pass
        
        return None
    except Exception:
        return None


def get_config() -> Dict[str, Any]:
    """读取配置文件"""
    config_file = Path("config/config.yaml")
    if not config_file.exists():
        return {}
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config.get('version', {})
    except Exception:
        return {}


def compare_versions(ver1: str, ver2: str) -> int:
    """比较两个版本号，返回-1(ver1<ver2), 0(ver1==ver2), 1(ver1>ver2)"""
    def version_tuple(v):
        return tuple(map(int, v[1:].split('.')))
    
    t1 = version_tuple(ver1)
    t2 = version_tuple(ver2)
    
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    else:
        return 0


def check_version_update() -> Dict[str, Any]:
    """检查版本更新"""
    result = {
        'need_update': False,
        'local_version': None,
        'remote_version': None,
        'auto_update_enabled': False,
        'flags': {}
    }
    
    # 读取配置
    config = get_config()
    auto_update_enabled = config.get('auto_update_enabled', False)
    result['auto_update_enabled'] = auto_update_enabled
    
    # 获取本地版本
    local_version = get_local_version()
    result['local_version'] = local_version
    
    # 获取远程版本
    remote_version = get_remote_version()
    result['remote_version'] = remote_version
    
    if not local_version or not remote_version:
        return result
    
    # 比较版本
    if compare_versions(local_version, remote_version) < 0:
        result['need_update'] = True
        
        # 尝试获取远程版本的标志信息
        remote_info = get_remote_version_info(remote_version)
        if remote_info:
            result['flags'] = remote_info.get('flags', {})
    
    return result


def main():
    """主函数"""
    check_result = check_version_update()
    
    # 输出结果（JSON格式，便于脚本调用）
    print(json.dumps(check_result, indent=2, ensure_ascii=False))
    
    # 如果需要更新且启用自动更新，返回非零退出码
    if check_result.get('need_update') and check_result.get('auto_update_enabled'):
        sys.exit(1)  # 返回1表示需要更新
    else:
        sys.exit(0)  # 返回0表示不需要更新或未启用自动更新


if __name__ == "__main__":
    main()

