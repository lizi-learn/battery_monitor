#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取 BMS MODBUS 协议.pdf，提取全部文字并整理输出到 test.txt
依赖: pip install pymupdf
"""

import sys
from pathlib import Path

# 使用 PyMuPDF (fitz) 读取 PDF，对中文和表格支持较好
try:
    import fitz  # PyMuPDF
except ImportError:
    print("请先安装: pip install pymupdf")
    sys.exit(1)

# PDF 与输出路径（与脚本同目录）
SCRIPT_DIR = Path(__file__).resolve().parent
PDF_PATH = SCRIPT_DIR / "BMS MODBUS 协议.pdf"
OUTPUT_PATH = SCRIPT_DIR / "test.txt"


def read_pdf_to_text(pdf_path: Path) -> str:
    """逐页读取 PDF 文字，按页整理，保证完整。"""
    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到文件: {pdf_path}")
    lines = []
    with fitz.open(pdf_path) as doc:
        total = len(doc)
        for i in range(total):
            page = doc[i]
            # sort=True 有助于按阅读顺序排列文字
            text = page.get_text(sort=True)
            text = text.strip()
            if text:
                lines.append(f"========== 第 {i + 1} 页 / 共 {total} 页 ==========")
                lines.append("")
                lines.append(text)
                lines.append("")
    return "\n".join(lines)


def main():
    print(f"正在读取: {PDF_PATH}")
    raw = read_pdf_to_text(PDF_PATH)
    # 整理：合并多余空行，保留段落结构
    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    body = "\n\n".join(paragraphs)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write("===== BMS MODBUS 协议（从 PDF 完整提取） =====\n\n")
        f.write(body)
        if not body.endswith("\n"):
            f.write("\n")
    print(f"已写入: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
