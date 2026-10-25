from User import User
from Customer import Customer
from Manager import Manager
from Event import Event
from Registration import Registration
from DataSource import DataSource
from UserState import UserState
from CustomerState import CustomerState
from ManagerState import ManagerState


class Adapter:
    STATES: dict[type, type[UserState]] = {
        Customer: CustomerState,
        Manager: ManagerState,
    }

    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.state: UserState | None = None

    def login(self, user: User):
        state_class = self.STATES.get(type(user))
        if state_class is None:
            raise PermissionError(f"No state defined for {type(user).__name__}")
        self.state = state_class(user, self.data_source)

    def logout(self):
        self.state = None

    def _current_state(self) -> UserState:
        if self.state is None:
            raise PermissionError("No user logged in")
        return self.state

    def view_events(self) -> list[Event]:
        return self._current_state().view_events()

    def create_user(self, user: User):
        self._current_state().create_user(user)

    def create_registration(self, registration_id: int, event_id: int, user_id: int | None = None) -> Registration:
        return self._current_state().create_registration(registration_id, event_id, user_id)

    def update_registration(self, registration_id: int, event_id: int | None = None, user_id: int | None = None) -> Registration:
        return self._current_state().update_registration(registration_id, event_id, user_id)

    def view_registrations(self) -> list[Registration]:
        return self._current_state().view_registrations()

    def cancel_registration(self, registration_id: int):
        self._current_state().cancel_registration(registration_id)

    def add_event(self, event: Event):
        self._current_state().add_event(event)

    def update_event(self, event_id: int, name: str, capacity: int):
        self._current_state().update_event(event_id, name, capacity)

    def remove_event(self, event_id: int):
        self._current_state().remove_event(event_id)
