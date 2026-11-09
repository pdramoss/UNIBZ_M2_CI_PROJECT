import argparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(BASE_DIR, folder) for folder in ("Models", "States", "Storage")] + [BASE_DIR]

from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from DataSource import DataSource
from Adapter import Adapter
from BaseStorage import BaseStorage
from StorageFactory import create_storage
from Services import next_id, find_user_by_name, resolve_attendee, available_places, login_user
from Localizable import Msg, Role

USAGE = """eventsHolidays.py COMMAND [OPTIONS]

Commands:
  login --role {manager,customer} --name NAME --password PASSWORD [--age N]
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


def print_event(data_source: DataSource, event: Event):
    print(Msg.EVENT_LINE.format(id=event.id, name=event.name, capacity=event.capacity,
                                available=available_places(data_source, event)))


def print_registration(registration: Registration):
    print(Msg.REGISTRATION_LINE.format(id=registration.id, event_id=registration.eventId,
                                       user_name=registration.userName, user_id=registration.userId))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eventsHolidays.py", usage=USAGE)
    commands = parser.add_subparsers(dest="command", required=True)

    login = commands.add_parser("login", help="log in as a manager or a customer")
    login.add_argument("--role", choices=list(Role.ALL), required=True)
    login.add_argument("--name", required=True)
    login.add_argument("--password", required=True)
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


def run_login(storage: BaseStorage, data_source: DataSource, args):
    user = login_user(data_source, args.role, args.name, args.password, args.age)
    storage.save_session(user.id)
    print(Msg.LOGGED_IN.format(type=type(user).__name__, name=user.name, id=user.id))


def run_event(adapter: Adapter, data_source: DataSource, args):
    if args.action == "list":
        for event in adapter.view_events():
            print_event(data_source, event)
    elif args.action == "add":
        event = Event(next_id(data_source.events), args.name, args.capacity)
        adapter.add_event(event)
        print(Msg.EVENT_CREATED.format(id=event.id))
    elif args.action == "update":
        current = data_source.get_event(args.id)
        name = current.name if args.name is None else args.name
        capacity = current.capacity if args.capacity is None else args.capacity
        adapter.update_event(args.id, name, capacity)
        print(Msg.EVENT_UPDATED.format(id=args.id))
    elif args.action == "remove":
        adapter.remove_event(args.id)
        print(Msg.EVENT_REMOVED.format(id=args.id))
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
        print(Msg.REGISTRATION_CREATED.format(id=registration.id))
    elif args.action == "change":
        user_id = None if args.attendee is None else resolve_attendee(adapter, data_source, args.attendee)
        adapter.update_registration(args.id, user_id=user_id)
        print(Msg.REGISTRATION_UPDATED.format(id=args.id))
    elif args.action == "cancel":
        adapter.cancel_registration(args.id)
        print(Msg.REGISTRATION_CANCELLED.format(id=args.id))


def main():
    args = build_parser().parse_args()
    storage = create_storage(BASE_DIR)
    data_source = storage.load()

    if args.command == "login":
        run_login(storage, data_source, args)
        storage.save(data_source)
        return
    if args.command == "logout":
        storage.clear_session()
        print(Msg.LOGGED_OUT)
        return

    adapter = Adapter(data_source)
    user_id = storage.load_session()
    if user_id is not None and user_id in data_source.users:
        adapter.login(data_source.get_user(user_id))

    if args.command == "whoami":
        if adapter.state is None:
            print(Msg.NO_USER_LOGGED_IN)
        else:
            user = adapter.state.user
            print(Msg.WHOAMI.format(type=type(user).__name__, name=user.name, id=user.id))
        return

    if args.command == "event":
        run_event(adapter, data_source, args)
    else:
        run_registration(adapter, data_source, args)
    storage.save(data_source)


if __name__ == "__main__":
    try:
        main()
    except (PermissionError, ValueError) as error:
        print(Msg.ERROR.format(error=error))
        sys.exit(1)
    except KeyError as error:
        print(Msg.ERROR.format(error=error.args[0]))
        sys.exit(1)
    except Exception as error:
        if not type(error).__module__.startswith("pymysql"):
            raise
        print(Msg.DATABASE_ERROR.format(error=error))
        sys.exit(1)
