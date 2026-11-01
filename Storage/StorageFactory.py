import os

from BaseStorage import BaseStorage
from JsonStorage import JsonStorage


def create_storage(default_data_dir: str) -> BaseStorage:
    if os.environ.get("DB_HOST"):
        from MySqlStorage import MySqlStorage

        return MySqlStorage(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", "3306")),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
        )
    return JsonStorage(os.environ.get("EVENTS_DATA_DIR", default_data_dir))
