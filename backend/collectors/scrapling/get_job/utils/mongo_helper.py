"""MongoDB 辅助工具"""

from pymongo import MongoClient


class MongoHelper:
    """MongoDB 操作封装"""

    def __init__(self, settings: dict):
        self.uri = settings.get("MONGODB_URI", "mongodb://localhost:27017")
        self.database = settings.get("MONGODB_DATABASE", "jobs")
        self.client: MongoClient | None = None
        self.db = None

    def connect(self):
        self.client = MongoClient(self.uri)
        self.db = self.client[self.database]
        return self.db

    def close(self):
        if self.client:
            self.client.close()

    def insert_one(self, collection: str, data: dict) -> str:
        if self.db is None:
            self.connect()
        return str(self.db[collection].insert_one(data).inserted_id)

    def find(
        self, collection: str, query: dict | None = None, limit: int = 100
    ) -> list[dict]:
        if self.db is None:
            self.connect()
        return list(self.db[collection].find(query or {}, limit=limit))

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
