"""Use cases shared by the CLI (eventsHolidays.py) and the REST API (api.py)."""
from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from DataSource import DataSource
from Adapter import Adapter
from Localizable import Msg, Role

ROLES = {Role.MANAGER: Manager, Role.CUSTOMER: Customer}


def next_id(items: dict) -> int:
    return max(items, default=0) + 1


def find_user_by_name(data_source: DataSource, name: str, user_type: type | None = None) -> User | None:
    for user in data_source.users.values():
        if user.name == name and (user_type is None or type(user) is user_type):
            return user
    return None


def resolve_attendee(adapter: Adapter, data_source: DataSource, name: str) -> int:
    user = find_user_by_name(data_source, name)
    if user is None:
        user = Customer(next_id(data_source.users), name, 0, 0)
        adapter.create_user(user)
    return user.id


def available_places(data_source: DataSource, event: Event) -> int:
    taken = sum(1 for r in data_source.get_registrations() if r.eventId == event.id)
    return event.capacity - taken


def login_user(data_source: DataSource, role: str, name: str, password: str, age: int = 0) -> User:
    """Log in an existing user, or register a new one with that role."""
    user_type = ROLES.get(role)
    if user_type is None:
        raise ValueError(Msg.UNKNOWN_ROLE.format(role=role))
    user = find_user_by_name(data_source, name, user_type)
    if user is None:
        user = user_type(next_id(data_source.users), name, age, 0, password)
        if user_type is Manager:
            data_source.add_manager(user)
        else:
            data_source.add_customer(user)
    elif user.password is None:
        # Users created without a password (e.g. by a manager with --attendee) set it on their first login
        user.set_password(password)
    elif not user.check_password(password):
        raise PermissionError(Msg.INVALID_PASSWORD)
    return user
