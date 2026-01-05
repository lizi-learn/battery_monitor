"""
版本信息模块
包含版本号、特殊标志和版本检查功能
"""

import json
import os
from typing import Optional, Dict, Any
from pathlib import Path


class VersionInfo:
    """版本信息类"""
    
    def __init__(self, version: str, build_hash: str = "", flags: Dict[str, Any] = None):
        """
        初始化版本信息
        
        Args:
            version: 版本号，格式如 "v1.0.0"
            build_hash: 构建哈希值（Git commit hash）
            flags: 特殊标志字典，用于标识特定功能或代码
        """
        self.version = version
        self.build_hash = build_hash
        self.flags = flags or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version": self.version,
            "build_hash": self.build_hash,
            "flags": self.flags
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionInfo':
        """从字典创建"""
        return cls(
            version=data.get("version", ""),
            build_hash=data.get("build_hash", ""),
            flags=data.get("flags", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'VersionInfo':
        """从JSON字符串创建"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_file(cls, file_path: str) -> Optional['VersionInfo']:
        """从文件加载版本信息"""
        path = Path(file_path)
        if not path.exists():
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception:
            return None
    
    def has_flag(self, flag_name: str) -> bool:
        """检查是否包含特定标志"""
        return self.flags.get(flag_name, False)
    
    def get_flag(self, flag_name: str, default: Any = None) -> Any:
        """获取标志值"""
        return self.flags.get(flag_name, default)
    
    def save(self, file_path: str) -> bool:
        """保存到文件"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
            return True
        except Exception:
            return False


def get_version_info(version_file: str = "VERSION.json") -> Optional[VersionInfo]:
    """
    获取版本信息
    
    Args:
        version_file: 版本文件路径，默认在当前目录查找
        
    Returns:
        VersionInfo对象，如果文件不存在则返回None
    """
    # 尝试多个可能的路径
    paths = [
        Path(version_file),  # 直接指定的路径
        Path(__file__).parent.parent / version_file,  # 项目根目录
        Path.cwd() / version_file,  # 当前工作目录
    ]
    
    for path in paths:
        if path.exists():
            return VersionInfo.from_file(str(path))
    
    return None


def get_version() -> str:
    """获取版本号字符串"""
    version_info = get_version_info()
    if version_info:
        return version_info.version
    return "unknown"


__all__ = ['VersionInfo', 'get_version_info', 'get_version']

