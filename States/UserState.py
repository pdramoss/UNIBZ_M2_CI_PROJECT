from abc import ABC

from User import User
from Event import Event
from Registration import Registration
from DataSource import DataSource
from Localizable import Msg


class EventFullError(ValueError):
    """Raised when an event has no places left."""


class UserState(ABC):
    def __init__(self, user: User, data_source: DataSource):
        self.user = user
        self.data_source = data_source

    def _deny(self, action: str):
        raise PermissionError(Msg.CANNOT.format(type=type(self.user).__name__, action=action))

    def view_events(self) -> list[Event]:
        self._deny(Msg.ACTION_VIEW_EVENTS)

    def create_user(self, user: User):
        self._deny(Msg.ACTION_CREATE_USERS)

    def create_registration(self, registration_id: int, event_id: int, user_id: int | None = None) -> Registration:
        self._deny(Msg.ACTION_CREATE_REGISTRATIONS)

    def update_registration(self, registration_id: int, event_id: int | None = None, user_id: int | None = None) -> Registration:
        self._deny(Msg.ACTION_UPDATE_REGISTRATIONS)

    def view_registrations(self) -> list[Registration]:
        self._deny(Msg.ACTION_VIEW_REGISTRATIONS)

    def cancel_registration(self, registration_id: int):
        self._deny(Msg.ACTION_CANCEL_REGISTRATIONS)

    def add_event(self, event: Event):
        self._deny(Msg.ACTION_ADD_EVENTS)

    def update_event(self, event_id: int, name: str, capacity: int):
        self._deny(Msg.ACTION_UPDATE_EVENTS)

    def remove_event(self, event_id: int):
        self._deny(Msg.ACTION_REMOVE_EVENTS)

    def _check_capacity(self, event: Event):
        taken = sum(1 for r in self.data_source.get_registrations() if r.eventId == event.id)
        if taken >= event.capacity:
            raise EventFullError(Msg.EVENT_FULL.format(id=event.id))

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
