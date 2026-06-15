#!/usr/bin/env python
"""Scrapling 爬虫运行入口"""

import sys
from pathlib import Path

# 将项目根目录加入 sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from scrapy.cmdline import execute


def main():
    """运行爬虫"""
    if len(sys.argv) > 1:
        spider_name = sys.argv[1]
        execute(argv=["scrapy", "crawl", spider_name, *sys.argv[2:]])
    else:
        print("Usage: python run.py <spider_name> [options]")
        print("Available spiders: xiaoyuan, liepin")
        sys.exit(1)


if __name__ == "__main__":
    main()
