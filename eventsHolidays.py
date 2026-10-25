import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(BASE_DIR, "Models"), os.path.join(BASE_DIR, "States"), BASE_DIR]

from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from DataSource import DataSource
from Adapter import Adapter

DATA_DIR = os.environ.get("EVENTS_DATA_DIR", BASE_DIR)
DATA_FILE = os.path.join(DATA_DIR, "data.json")
SESSION_FILE = os.path.join(DATA_DIR, "session.json")

USAGE = """eventsHolidays.py COMMAND [OPTIONS]

Commands:
  login --role {manager,customer} --name NAME [--age N]
  whoami
  logout
  event list
  event add --name NAME --capacity NUMBER
  event update ID [--name NAME] [--capacity NUMBER]
  event remove ID
  event search --available-places NUMBER
  registration list
  registration create --event ID --attendee NAME
  registration change ID [--attendee NAME]
  registration cancel ID"""


def load() -> DataSource:
    data_source = DataSource()
    if not os.path.exists(DATA_FILE):
        return data_source
    with open(DATA_FILE) as file:
        data = json.load(file)
    for item in data["users"]:
        if item["type"] == "Customer":
            data_source.add_customer(Customer(item["id"], item["name"], item["age"], item.get("id_registration", 0)))
        elif item["type"] == "Manager":
            data_source.add_manager(Manager(item["id"], item["name"], item["age"], item.get("id_event", 0)))
        else:
            data_source.add_user(User(item["id"], item["name"], item["age"]))
    for item in data["events"]:
        data_source.add_event(Event(item["id"], item["name"], item["capacity"]))
    for item in data["registrations"]:
        user = data_source.get_user(item["userId"])
        event = data_source.get_event(item["eventId"])
        data_source.add_registration(Registration(item["id"], user, event))
    return data_source


def save(data_source: DataSource):
    data = {
        "users": [{"type": type(user).__name__, **vars(user)} for user in data_source.users.values()],
        "events": [vars(event) for event in data_source.get_events()],
        "registrations": [vars(registration) for registration in data_source.get_registrations()],
    }
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=2)


def load_session() -> int | None:
    if not os.path.exists(SESSION_FILE):
        return None
    with open(SESSION_FILE) as file:
        return json.load(file)["user_id"]


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


def print_event(data_source: DataSource, event: Event):
    print(f"[{event.id}] {event.name} - capacity {event.capacity}, available {available_places(data_source, event)}")


def print_registration(registration: Registration):
    print(f"[{registration.id}] event {registration.eventId} - {registration.userName} (user {registration.userId})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eventsHolidays.py", usage=USAGE)
    commands = parser.add_subparsers(dest="command", required=True)

    login = commands.add_parser("login", help="log in as a manager or a customer")
    login.add_argument("--role", choices=["manager", "customer"], required=True)
    login.add_argument("--name", required=True)
    login.add_argument("--age", type=int, default=0)
    commands.add_parser("whoami", help="show the current user")
    commands.add_parser("logout", help="close the current session")

    event = commands.add_parser("event").add_subparsers(dest="action", required=True)
    event.add_parser("list")
    add = event.add_parser("add")
    add.add_argument("--name", required=True)
    add.add_argument("--capacity", type=int, required=True)
    update = event.add_parser("update")
    update.add_argument("id", type=int)
    update.add_argument("--name")
    update.add_argument("--capacity", type=int)
    remove = event.add_parser("remove")
    remove.add_argument("id", type=int)
    search = event.add_parser("search")
    search.add_argument("--available-places", type=int, required=True)

    registration = commands.add_parser("registration").add_subparsers(dest="action", required=True)
    registration.add_parser("list")
    create = registration.add_parser("create")
    create.add_argument("--event", type=int, required=True)
    create.add_argument("--attendee", required=True)
    change = registration.add_parser("change")
    change.add_argument("id", type=int)
    change.add_argument("--attendee")
    cancel = registration.add_parser("cancel")
    cancel.add_argument("id", type=int)

    return parser


def run_login(data_source: DataSource, args):
    user_type = Manager if args.role == "manager" else Customer
    user = find_user_by_name(data_source, args.name, user_type)
    if user is None:
        user = user_type(next_id(data_source.users), args.name, args.age, 0)
        if user_type is Manager:
            data_source.add_manager(user)
        else:
            data_source.add_customer(user)
    with open(SESSION_FILE, "w") as file:
        json.dump({"user_id": user.id}, file)
    print(f"Logged in as {type(user).__name__} {user.name} (id {user.id})")


def run_event(adapter: Adapter, data_source: DataSource, args):
    if args.action == "list":
        for event in adapter.view_events():
            print_event(data_source, event)
    elif args.action == "add":
        event = Event(next_id(data_source.events), args.name, args.capacity)
        adapter.add_event(event)
        print(f"Event {event.id} created")
    elif args.action == "update":
        current = data_source.get_event(args.id)
        name = current.name if args.name is None else args.name
        capacity = current.capacity if args.capacity is None else args.capacity
        adapter.update_event(args.id, name, capacity)
        print(f"Event {args.id} updated")
    elif args.action == "remove":
        adapter.remove_event(args.id)
        print(f"Event {args.id} removed")
    elif args.action == "search":
        for event in adapter.view_events():
            if available_places(data_source, event) >= args.available_places:
                print_event(data_source, event)


def run_registration(adapter: Adapter, data_source: DataSource, args):
    if args.action == "list":
        for registration in adapter.view_registrations():
            print_registration(registration)
    elif args.action == "create":
        user_id = resolve_attendee(adapter, data_source, args.attendee)
        registration = adapter.create_registration(next_id(data_source.registrations), args.event, user_id)
        print(f"Registration {registration.id} created")
    elif args.action == "change":
        user_id = None if args.attendee is None else resolve_attendee(adapter, data_source, args.attendee)
        adapter.update_registration(args.id, user_id=user_id)
        print(f"Registration {args.id} updated")
    elif args.action == "cancel":
        adapter.cancel_registration(args.id)
        print(f"Registration {args.id} cancelled")


def main():
    args = build_parser().parse_args()
    data_source = load()

    if args.command == "login":
        run_login(data_source, args)
        save(data_source)
        return
    if args.command == "logout":
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
        print("Logged out")
        return

    adapter = Adapter(data_source)
    user_id = load_session()
    if user_id is not None and user_id in data_source.users:
        adapter.login(data_source.get_user(user_id))

    if args.command == "whoami":
        if adapter.state is None:
            print("No user logged in")
        else:
            user = adapter.state.user
            print(f"{type(user).__name__} {user.name} (id {user.id})")
        return

    if args.command == "event":
        run_event(adapter, data_source, args)
    else:
        run_registration(adapter, data_source, args)
    save(data_source)


if __name__ == "__main__":
    try:
        main()
    except (PermissionError, ValueError) as error:
        print(f"Error: {error}")
        sys.exit(1)
    except KeyError as error:
        print(f"Error: {error.args[0]}")
        sys.exit(1)
