import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Same import paths as eventsHolidays.py / api.py
sys.path[:0] = [os.path.join(ROOT, folder) for folder in ("Models", "States", "Storage")] + [ROOT]
os.environ.pop("DB_HOST", None)  # tests always use JSON storage

from Adapter import Adapter  # noqa: E402
from Customer import Customer  # noqa: E402
from DataSource import DataSource  # noqa: E402
from Event import Event  # noqa: E402
from Manager import Manager  # noqa: E402


class World:
    """A small data set: one manager, two customers and one event with 2 places."""

    def __init__(self):
        self.data = DataSource()
        self.manager = Manager(1, "Luis", 40, 0, "luis123")
        self.ana = Customer(2, "Ana", 30, 0, "ana123")
        self.bob = Customer(3, "Bob", 25, 0, "bob123")
        self.data.add_manager(self.manager)
        self.data.add_customer(self.ana)
        self.data.add_customer(self.bob)
        self.concert = Event(1, "Concert", 2)
        self.data.add_event(self.concert)

    def as_user(self, user) -> Adapter:
        adapter = Adapter(self.data)
        adapter.login(user)
        return adapter


@pytest.fixture
def world() -> World:
    return World()
