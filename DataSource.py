from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from Localizable import Msg


class DataSource:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.customers: dict[int, Customer] = {}
        self.managers: dict[int, Manager] = {}
        self.events: dict[int, Event] = {}
        self.registrations: dict[int, Registration] = {}

    def add_user(self, user: User):
        self.users[user.id] = user

    def add_customer(self, customer: Customer):
        self.customers[customer.id] = customer
        self.add_user(customer)

    def add_manager(self, manager: Manager):
        self.managers[manager.id] = manager
        self.add_user(manager)

    def get_user(self, user_id: int) -> User:
        if user_id not in self.users:
            raise KeyError(Msg.USER_NOT_FOUND.format(id=user_id))
        return self.users[user_id]

    def add_event(self, event: Event):
        self.events[event.id] = event

    def get_event(self, event_id: int) -> Event:
        if event_id not in self.events:
            raise KeyError(Msg.EVENT_NOT_FOUND.format(id=event_id))
        return self.events[event_id]

    def get_events(self) -> list[Event]:
        return list(self.events.values())

    def update_event(self, event: Event):
        self.get_event(event.id)
        self.events[event.id] = event

    def remove_event(self, event_id: int):
        self.get_event(event_id)
        del self.events[event_id]

    def add_registration(self, registration: Registration):
        self.registrations[registration.id] = registration

    def get_registration(self, registration_id: int) -> Registration:
        if registration_id not in self.registrations:
            raise KeyError(Msg.REGISTRATION_NOT_FOUND.format(id=registration_id))
        return self.registrations[registration_id]

    def get_registrations(self) -> list[Registration]:
        return list(self.registrations.values())

    def update_registration(self, registration: Registration):
        self.get_registration(registration.id)
        self.registrations[registration.id] = registration

    def remove_registration(self, registration_id: int):
        self.get_registration(registration_id)
        del self.registrations[registration_id]
