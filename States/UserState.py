from abc import ABC

from User import User
from Event import Event
from Registration import Registration
from DataSource import DataSource


class UserState(ABC):
    def __init__(self, user: User, data_source: DataSource):
        self.user = user
        self.data_source = data_source

    def _deny(self, action: str):
        raise PermissionError(f"{type(self.user).__name__} cannot {action}")

    def view_events(self) -> list[Event]:
        self._deny("view events")

    def create_user(self, user: User):
        self._deny("create users")

    def create_registration(self, registration_id: int, event_id: int, user_id: int | None = None) -> Registration:
        self._deny("create registrations")

    def update_registration(self, registration_id: int, event_id: int | None = None, user_id: int | None = None) -> Registration:
        self._deny("update registrations")

    def view_registrations(self) -> list[Registration]:
        self._deny("view registrations")

    def cancel_registration(self, registration_id: int):
        self._deny("cancel registrations")

    def add_event(self, event: Event):
        self._deny("add events")

    def update_event(self, event_id: int, name: str, capacity: int):
        self._deny("update events")

    def remove_event(self, event_id: int):
        self._deny("remove events")

    def _check_capacity(self, event: Event):
        taken = sum(1 for r in self.data_source.get_registrations() if r.eventId == event.id)
        if taken >= event.capacity:
            raise ValueError(f"Event {event.id} is full")

    def _register(self, registration_id: int, event_id: int, user: User) -> Registration:
        event = self.data_source.get_event(event_id)
        self._check_capacity(event)
        registration = Registration(registration_id, user, event)
        self.data_source.add_registration(registration)
        return registration

    def _change_registration(self, registration: Registration, event_id: int | None = None, user_id: int | None = None) -> Registration:
        event = self.data_source.get_event(registration.eventId if event_id is None else event_id)
        if registration.eventId != event.id:
            self._check_capacity(event)
        user = self.data_source.get_user(registration.userId if user_id is None else user_id)
        updated = Registration(registration.id, user, event)
        self.data_source.update_registration(updated)
        return updated
