import os

from BaseStorage import BaseStorage
from JsonStorage import JsonStorage
from Localizable import Env, Defaults


def create_storage(default_data_dir: str) -> BaseStorage:
    if os.environ.get(Env.DB_HOST):
        from MySqlStorage import MySqlStorage

        return MySqlStorage(
            host=os.environ[Env.DB_HOST],
            port=int(os.environ.get(Env.DB_PORT, Defaults.DB_PORT)),
            database=os.environ[Env.DB_NAME],
            user=os.environ[Env.DB_USER],
            password=os.environ[Env.DB_PASSWORD],
        )
    return JsonStorage(os.environ.get(Env.EVENTS_DATA_DIR, default_data_dir))
