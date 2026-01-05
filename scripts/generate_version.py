#!/usr/bin/env python3
"""
版本信息生成脚本
在git-push时自动生成VERSION.json文件
"""

import json
import subprocess
import sys
from pathlib import Path
import yaml


def get_git_commit_hash() -> str:
    """获取当前Git commit hash"""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_config_flags(config_path: str = "config/config.yaml") -> dict:
    """从配置文件读取版本标志"""
    try:
        config_file = Path(config_path)
        if not config_file.exists():
            return {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        version_config = config.get('version', {})
        flags = version_config.get('flags', {})
        return flags
    except Exception:
        return {}


def generate_version_file(version: str, output_path: str = "VERSION.json", config_path: str = "config/config.yaml"):
    """
    生成版本信息文件
    
    Args:
        version: 版本号，格式如 "v1.0.0"
        output_path: 输出文件路径
        config_path: 配置文件路径
    """
    build_hash = get_git_commit_hash()
    flags = get_config_flags(config_path)
    
    version_info = {
        "version": version,
        "build_hash": build_hash,
        "flags": flags
    }
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)
    
    print(f"版本信息文件已生成: {output_path}")
    print(f"版本: {version}")
    print(f"构建哈希: {build_hash}")
    if flags:
        print(f"标志: {json.dumps(flags, ensure_ascii=False)}")
    
    return version_info


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python generate_version.py <版本号> [输出路径] [配置路径]")
        sys.exit(1)
    
    version = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "VERSION.json"
    config_path = sys.argv[3] if len(sys.argv) > 3 else "config/config.yaml"
    
    generate_version_file(version, output_path, config_path)

