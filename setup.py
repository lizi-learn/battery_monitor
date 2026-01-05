"""
BMS 电池管理系统监测工具安装脚本
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取 README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

setup(
    name="bms-monitor",
    version="1.0.0",
    description="BMS 电池管理系统监测工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BMS Monitor Team",
    packages=find_packages(),
    install_requires=[
        "pyserial>=3.5",
        "PyYAML>=6.0",
    ],
    python_requires=">=3.6",
    entry_points={
        "console_scripts": [
            "bms-monitor=src.bms_monitor:main",
            "bms-scanner=src.bms_scanner:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)

