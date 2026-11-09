import json
import os

from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from DataSource import DataSource
from BaseStorage import BaseStorage
from Localizable import Defaults


class JsonStorage(BaseStorage):
    def __init__(self, data_dir: str):
        self.data_file = os.path.join(data_dir, Defaults.DATA_FILE)
        self.session_file = os.path.join(data_dir, Defaults.SESSION_FILE)

    def load(self) -> DataSource:
        data_source = DataSource()
        if not os.path.exists(self.data_file):
            return data_source
        with open(self.data_file) as file:
            data = json.load(file)
        for item in data["users"]:
            if item["type"] == "Customer":
                user = Customer(item["id"], item["name"], item["age"], item.get("id_registration", 0))
                data_source.add_customer(user)
            elif item["type"] == "Manager":
                user = Manager(item["id"], item["name"], item["age"], item.get("id_event", 0))
                data_source.add_manager(user)
            else:
                user = User(item["id"], item["name"], item["age"])
                data_source.add_user(user)
            # Already hashed: assign it directly instead of calling set_password
            user.password = item.get("password")
        for item in data["events"]:
            data_source.add_event(Event(item["id"], item["name"], item["capacity"]))
        for item in data["registrations"]:
            user = data_source.get_user(item["userId"])
            event = data_source.get_event(item["eventId"])
            data_source.add_registration(Registration(item["id"], user, event))
        return data_source

    def save(self, data_source: DataSource):
        data = {
            "users": [{"type": type(user).__name__, **vars(user)} for user in data_source.users.values()],
            "events": [vars(event) for event in data_source.get_events()],
            "registrations": [vars(registration) for registration in data_source.get_registrations()],
        }
        with open(self.data_file, "w") as file:
            json.dump(data, file, indent=2)

    def load_session(self) -> int | None:
        if not os.path.exists(self.session_file):
            return None
        with open(self.session_file) as file:
            return json.load(file)["user_id"]

    def save_session(self, user_id: int):
        with open(self.session_file, "w") as file:
            json.dump({"user_id": user_id}, file)

    def clear_session(self):
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
