"""猎聘网工具函数"""

import re
import time
from pathlib import Path


def extract_json_from_scripts(html_text: str, patterns: list[str] = None) -> dict | None:
    """从 script 标签中提取 JSON 数据"""
    if patterns is None:
        patterns = [
            r"window\.__INITIAL_STATE__\s*=\s*({.*?});",
            r"window\.__PRELOADED_STATE__\s*=\s*({.*?});",
        ]
    for pattern in patterns:
        match = re.search(pattern, html_text, re.DOTALL)
        if match:
            import json

            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue
    return None


def parse_salary(salary_text: str) -> tuple[int | None, int | None]:
    """解析薪资范围"""
    if not salary_text:
        return None, None
    numbers = re.findall(r"\d+", salary_text.replace(",", ""))
    if len(numbers) >= 2:
        return int(numbers[0]), int(numbers[1])
    elif len(numbers) == 1:
        return int(numbers[0]), int(numbers[0])
    return None, None


def save_debug_page(response, spider, suffix: str = "debug") -> None:
    """保存调试页面"""
    debug_dir = Path(__file__).parent.parent.parent.parent / "log" / "crawler_debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    filename = debug_dir / f"{spider.name}_{suffix}_{int(time.time())}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(response.text[:20000])
    spider.logger.info(f"Debug page saved: {filename}")
