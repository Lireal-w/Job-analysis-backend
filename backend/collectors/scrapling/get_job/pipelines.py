import csv
import json
import os
from datetime import datetime
from pathlib import Path

from itemadapter import ItemAdapter

from get_job.items import XiaoyuanJobItem


class DataCleanPipeline:
    """数据清洗：统一字段格式"""

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # 清理字符串字段
        for field_name in adapter.field_names():
            value = adapter.get(field_name)
            if isinstance(value, str):
                adapter[field_name] = value.strip()

        # 解析薪资
        salary_raw = adapter.get("salary_raw")
        if salary_raw and isinstance(salary_raw, str):
            import re

            numbers = re.findall(r"\d+", salary_raw)
            if len(numbers) >= 2:
                adapter["salary_min"] = int(numbers[0])
                adapter["salary_max"] = int(numbers[1])
            elif len(numbers) == 1:
                adapter["salary_min"] = int(numbers[0])
                adapter["salary_max"] = int(numbers[0])

        # 默认值
        if not adapter.get("crawl_time"):
            adapter["crawl_time"] = datetime.now().isoformat()
        if not adapter.get("source_platform"):
            adapter["source_platform"] = getattr(spider, "name", "unknown")

        return item


class JsonOutputPipeline:
    """JSON 文件输出"""

    def __init__(self):
        output_dir = Path(__file__).parent.parent.parent.parent / "static" / "crawl_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        self.items = []

    def process_item(self, item, spider):
        self.items.append(ItemAdapter(item).asdict())
        return item

    def close_spider(self, spider):
        if not self.items:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{spider.name}_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.items, f, ensure_ascii=False, indent=2)
        spider.logger.info(f"[JsonOutput] Saved {len(self.items)} items to {filename}")


class CsvOutputPipeline:
    """CSV 文件输出"""

    def __init__(self):
        output_dir = Path(__file__).parent.parent.parent.parent / "static" / "crawl_output"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir
        self.items = []

    def process_item(self, item, spider):
        self.items.append(ItemAdapter(item).asdict())
        return item

    def close_spider(self, spider):
        if not self.items:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"{spider.name}_{timestamp}.csv"
        if self.items:
            with open(filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=self.items[0].keys())
                writer.writeheader()
                writer.writerows(self.items)
        spider.logger.info(f"[CsvOutput] Saved {len(self.items)} items to {filename}")


class MongoPipeline:
    """MongoDB 存储（可选）"""

    def __init__(self):
        self.client = None
        self.db = None

    def open_spider(self, spider):
        try:
            from pymongo import MongoClient

            mongo_uri = spider.settings.get("MONGODB_URI")
            mongo_db = spider.settings.get("MONGODB_DATABASE")
            self.client = MongoClient(mongo_uri)
            self.db = self.client[mongo_db]
            spider.logger.info(f"[MongoPipeline] Connected to {mongo_db}")
        except Exception as e:
            spider.logger.warning(f"[MongoPipeline] MongoDB not available: {e}")

    def process_item(self, item, spider):
        if self.db is None:
            return item
        try:
            collection = self.db["jobs"]
            adapter = ItemAdapter(item)
            collection.insert_one(adapter.asdict())
        except Exception as e:
            spider.logger.error(f"[MongoPipeline] Insert failed: {e}")
        return item

    def close_spider(self, spider):
        if self.client:
            self.client.close()
