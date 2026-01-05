"""
BMS 电池管理系统监测工具
"""

from .version import get_version_info, get_version

# 尝试从VERSION.json获取版本信息，如果不存在则使用默认值
_version_info = get_version_info()
if _version_info:
    __version__ = _version_info.version
else:
    __version__ = "1.0.0"

__author__ = "BMS Monitor Team"

__all__ = ['__version__', '__author__', 'get_version_info', 'get_version']

