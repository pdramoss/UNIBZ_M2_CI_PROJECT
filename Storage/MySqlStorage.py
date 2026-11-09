import time

import pymysql

from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from DataSource import DataSource
from BaseStorage import BaseStorage


class MySqlStorage(BaseStorage):
    CONNECT_RETRIES = 10

    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.connection = self._connect(host=host, port=port, database=database, user=user, password=password)

    def _connect(self, **settings) -> pymysql.connections.Connection:
        for attempt in range(self.CONNECT_RETRIES):
            try:
                return pymysql.connect(**settings, autocommit=False, cursorclass=pymysql.cursors.DictCursor)
            except pymysql.err.OperationalError:
                if attempt == self.CONNECT_RETRIES - 1:
                    raise
                time.sleep(1)

    def load(self) -> DataSource:
        data_source = DataSource()
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT id, type, name, age, password, id_registration, id_event FROM users")
            for row in cursor.fetchall():
                if row["type"] == "Customer":
                    user = Customer(row["id"], row["name"], row["age"], row["id_registration"] or 0)
                    data_source.add_customer(user)
                elif row["type"] == "Manager":
                    user = Manager(row["id"], row["name"], row["age"], row["id_event"] or 0)
                    data_source.add_manager(user)
                else:
                    user = User(row["id"], row["name"], row["age"])
                    data_source.add_user(user)
                # Already hashed: assign it directly instead of calling set_password
                user.password = row["password"]
            cursor.execute("SELECT id, name, capacity FROM events")
            for row in cursor.fetchall():
                data_source.add_event(Event(row["id"], row["name"], row["capacity"]))
            cursor.execute("SELECT id, event_id, user_id FROM registrations")
            for row in cursor.fetchall():
                user = data_source.get_user(row["user_id"])
                event = data_source.get_event(row["event_id"])
                data_source.add_registration(Registration(row["id"], user, event))
        self.connection.commit()
        return data_source

    def save(self, data_source: DataSource):
        users = list(data_source.users.values())
        events = data_source.get_events()
        registrations = data_source.get_registrations()
        try:
            with self.connection.cursor() as cursor:
                # Delete children first and insert parents first, to respect the foreign keys
                self._delete_missing(cursor, "registrations", [r.id for r in registrations])
                self._delete_missing(cursor, "events", [e.id for e in events])
                self._delete_missing(cursor, "users", [u.id for u in users])
                cursor.executemany(
                    "INSERT INTO users (id, type, name, age, password, id_registration, id_event) VALUES (%s, %s, %s, %s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE type = VALUES(type), name = VALUES(name), age = VALUES(age), password = VALUES(password), "
                    "id_registration = VALUES(id_registration), id_event = VALUES(id_event)",
                    [(u.id, type(u).__name__, u.name, u.age, u.password, getattr(u, "id_registration", None), getattr(u, "id_event", None)) for u in users],
                )
                cursor.executemany(
                    "INSERT INTO events (id, name, capacity) VALUES (%s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE name = VALUES(name), capacity = VALUES(capacity)",
                    [(e.id, e.name, e.capacity) for e in events],
                )
                cursor.executemany(
                    "INSERT INTO registrations (id, event_id, user_id, user_name) VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE event_id = VALUES(event_id), user_id = VALUES(user_id), user_name = VALUES(user_name)",
                    [(r.id, r.eventId, r.userId, r.userName) for r in registrations],
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def _delete_missing(self, cursor, table: str, ids: list[int]):
        if ids:
            placeholders = ", ".join(["%s"] * len(ids))
            cursor.execute(f"DELETE FROM {table} WHERE id NOT IN ({placeholders})", ids)
        else:
            cursor.execute(f"DELETE FROM {table}")

    def close(self):
        self.connection.close()

    def load_session(self) -> int | None:
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT user_id FROM session WHERE id = 1")
            row = cursor.fetchone()
        self.connection.commit()
        return None if row is None else row["user_id"]

    def save_session(self, user_id: int):
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO session (id, user_id) VALUES (1, %s) ON DUPLICATE KEY UPDATE user_id = VALUES(user_id)",
                (user_id,),
            )
        self.connection.commit()

    def clear_session(self):
        with self.connection.cursor() as cursor:
            cursor.execute("DELETE FROM session WHERE id = 1")
        self.connection.commit()
