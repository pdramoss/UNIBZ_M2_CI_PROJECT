from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from UserState import UserState


class ManagerState(UserState):
    def view_events(self) -> list[Event]:
        return self.data_source.get_events()

    def add_event(self, event: Event):
        self.data_source.add_event(event)

    def update_event(self, event_id: int, name: str, capacity: int):
        self.data_source.update_event(Event(event_id, name, capacity))

    def remove_event(self, event_id: int):
        self.data_source.remove_event(event_id)

    def create_user(self, user: User):
        if isinstance(user, Customer):
            self.data_source.add_customer(user)
        elif isinstance(user, Manager):
            self.data_source.add_manager(user)
        else:
            self.data_source.add_user(user)

    def create_registration(self, registration_id: int, event_id: int, user_id: int | None = None) -> Registration:
        user = self.user if user_id is None else self.data_source.get_user(user_id)
        return self._register(registration_id, event_id, user)

    def update_registration(self, registration_id: int, event_id: int | None = None, user_id: int | None = None) -> Registration:
        return self._change_registration(self.data_source.get_registration(registration_id), event_id, user_id)

    def view_registrations(self) -> list[Registration]:
        return self.data_source.get_registrations()

    def cancel_registration(self, registration_id: int):
        self.data_source.remove_registration(registration_id)
