from Event import Event
from Registration import Registration
from UserState import UserState


class CustomerState(UserState):
    def view_events(self) -> list[Event]:
        return self.data_source.get_events()

    def create_registration(self, registration_id: int, event_id: int, user_id: int | None = None) -> Registration:
        if user_id is not None and user_id != self.user.id:
            raise PermissionError("Customer can only register themselves")
        return self._register(registration_id, event_id, self.user)

    def update_registration(self, registration_id: int, event_id: int | None = None, user_id: int | None = None) -> Registration:
        if user_id is not None and user_id != self.user.id:
            raise PermissionError("Customer can only register themselves")
        return self._change_registration(self._own_registration(registration_id), event_id, user_id)

    def view_registrations(self) -> list[Registration]:
        return [r for r in self.data_source.get_registrations() if r.userId == self.user.id]

    def cancel_registration(self, registration_id: int):
        self._own_registration(registration_id)
        self.data_source.remove_registration(registration_id)

    def _own_registration(self, registration_id: int) -> Registration:
        registration = self.data_source.get_registration(registration_id)
        if registration.userId != self.user.id:
            raise PermissionError("Customer can only manage their own registrations")
        return registration
