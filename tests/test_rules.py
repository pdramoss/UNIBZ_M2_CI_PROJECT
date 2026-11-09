"""Unit tests for the application's rules (domain layer, no web server)."""
import pytest

from Adapter import Adapter
from Customer import Customer
from Event import Event
from JsonStorage import JsonStorage
from Localizable import Msg, Role
from Manager import Manager
from Services import available_places, login_user, next_id, resolve_attendee
from User import User
from UserState import EventFullError


# ---------------- passwords ----------------

class TestPasswords:
    def test_password_is_stored_hashed_with_salt(self):
        user = User(1, "Ana", 30, "secret")
        assert user.password != "secret"
        salt, digest = user.password.split("$")
        assert len(salt) == 32 and len(digest) == 64

    def test_check_password(self):
        user = User(1, "Ana", 30, "secret")
        assert user.check_password("secret")
        assert not user.check_password("wrong")

    def test_same_password_gives_different_hashes(self):
        assert User(1, "A", 0, "same").password != User(2, "B", 0, "same").password

    def test_user_without_password_never_matches(self):
        assert not User(1, "Ana", 30).check_password("")


# ---------------- login / sign-up ----------------

class TestLogin:
    def test_new_name_signs_up_with_role(self, world):
        user = login_user(world.data, Role.CUSTOMER, "Carla", "pw", 22)
        assert isinstance(user, Customer) and user.id == 4 and user.age == 22
        assert world.data.get_user(4) is user

    def test_existing_user_logs_in(self, world):
        assert login_user(world.data, Role.MANAGER, "Luis", "luis123") is world.manager

    def test_wrong_password_is_refused(self, world):
        with pytest.raises(PermissionError, match=Msg.INVALID_PASSWORD):
            login_user(world.data, Role.MANAGER, "Luis", "bad")

    def test_unknown_role_is_rejected(self, world):
        with pytest.raises(ValueError):
            login_user(world.data, "admin", "Luis", "luis123")

    def test_user_created_without_password_sets_it_on_first_login(self, world):
        world.data.add_customer(Customer(10, "Dana", 0, 0))
        user = login_user(world.data, Role.CUSTOMER, "Dana", "first")
        assert user.id == 10 and user.check_password("first")
        with pytest.raises(PermissionError):
            login_user(world.data, Role.CUSTOMER, "Dana", "other")

    def test_same_name_can_be_manager_and_customer(self, world):
        customer_luis = login_user(world.data, Role.CUSTOMER, "Luis", "pw")
        assert isinstance(customer_luis, Customer) and customer_luis is not world.manager


# ---------------- ids ----------------

def test_next_id():
    assert next_id({}) == 1
    assert next_id({1: None, 2: None}) == 3
    assert next_id({1: None, 7: None}) == 8


# ---------------- authentication ----------------

def test_every_action_requires_login(world):
    adapter = Adapter(world.data)
    actions = [
        adapter.view_events,
        adapter.view_registrations,
        lambda: adapter.add_event(Event(9, "X", 1)),
        lambda: adapter.create_registration(1, 1),
        lambda: adapter.cancel_registration(1),
        lambda: adapter.remove_event(1),
    ]
    for action in actions:
        with pytest.raises(PermissionError, match=Msg.NO_USER_LOGGED_IN):
            action()


def test_logout_removes_permissions(world):
    adapter = world.as_user(world.manager)
    adapter.logout()
    with pytest.raises(PermissionError):
        adapter.view_events()


# ---------------- capacity ----------------

class TestCapacity:
    def test_available_places(self, world):
        manager = world.as_user(world.manager)
        assert available_places(world.data, world.concert) == 2
        manager.create_registration(1, 1, world.ana.id)
        assert available_places(world.data, world.concert) == 1

    def test_cannot_register_beyond_capacity(self, world):
        manager = world.as_user(world.manager)
        manager.create_registration(1, 1, world.ana.id)
        manager.create_registration(2, 1, world.bob.id)
        with pytest.raises(EventFullError, match=Msg.EVENT_FULL.format(id=1)):
            manager.create_registration(3, 1, world.manager.id)
        assert len(world.data.get_registrations()) == 2

    def test_event_full_is_a_value_error(self):
        # the CLI reports ValueError; EventFullError must stay compatible
        assert issubclass(EventFullError, ValueError)

    def test_cannot_move_registration_to_full_event(self, world):
        manager = world.as_user(world.manager)
        manager.add_event(Event(2, "Tiny", 1))
        manager.create_registration(1, 2, world.ana.id)
        manager.create_registration(2, 1, world.bob.id)
        with pytest.raises(EventFullError):
            manager.update_registration(2, event_id=2)

    def test_changing_attendee_in_a_full_event_is_allowed(self, world):
        manager = world.as_user(world.manager)
        manager.create_registration(1, 1, world.ana.id)
        manager.create_registration(2, 1, world.bob.id)
        updated = manager.update_registration(2, user_id=world.manager.id)
        assert updated.userName == "Luis" and updated.eventId == 1


# ---------------- manager rules ----------------

class TestManager:
    def test_event_crud(self, world):
        manager = world.as_user(world.manager)
        manager.add_event(Event(2, "Hike", 10))
        manager.update_event(2, "Long hike", 12)
        event = world.data.get_event(2)
        assert (event.name, event.capacity) == ("Long hike", 12)
        manager.remove_event(2)
        with pytest.raises(KeyError):
            world.data.get_event(2)

    def test_sees_every_registration(self, world):
        world.as_user(world.ana).create_registration(1, 1)
        world.as_user(world.bob).create_registration(2, 1)
        assert len(world.as_user(world.manager).view_registrations()) == 2

    def test_registers_any_user_and_creates_unknown_attendees(self, world):
        manager = world.as_user(world.manager)
        user_id = resolve_attendee(manager, world.data, "Zoe")
        new_user = world.data.get_user(user_id)
        assert isinstance(new_user, Customer) and new_user.password is None
        registration = manager.create_registration(1, 1, user_id)
        assert registration.userName == "Zoe"
        assert resolve_attendee(manager, world.data, "Zoe") == user_id  # no duplicate

    def test_removing_event_cancels_its_registrations(self, world):
        manager = world.as_user(world.manager)
        manager.add_event(Event(2, "Hike", 10))
        manager.create_registration(1, 1, world.ana.id)
        manager.create_registration(2, 2, world.bob.id)
        manager.remove_event(1)
        assert [r.id for r in world.data.get_registrations()] == [2]

    def test_removing_missing_event_raises(self, world):
        with pytest.raises(KeyError, match=Msg.EVENT_NOT_FOUND.format(id=99)):
            world.as_user(world.manager).remove_event(99)


# ---------------- customer rules ----------------

class TestCustomer:
    @pytest.mark.parametrize("action", [
        lambda a: a.add_event(Event(9, "X", 1)),
        lambda a: a.update_event(1, "X", 1),
        lambda a: a.remove_event(1),
        lambda a: a.create_user(Customer(9, "X", 0, 0)),
    ])
    def test_cannot_manage_events_or_users(self, world, action):
        with pytest.raises(PermissionError):
            action(world.as_user(world.ana))

    def test_can_view_events(self, world):
        assert world.as_user(world.ana).view_events() == [world.concert]

    def test_registers_only_themselves(self, world):
        ana = world.as_user(world.ana)
        assert ana.create_registration(1, 1).userId == world.ana.id
        with pytest.raises(PermissionError, match=Msg.CUSTOMER_SELF_ONLY):
            ana.create_registration(2, 1, world.bob.id)

    def test_sees_only_own_registrations(self, world):
        world.as_user(world.ana).create_registration(1, 1)
        world.as_user(world.bob).create_registration(2, 1)
        assert [r.id for r in world.as_user(world.ana).view_registrations()] == [1]

    def test_cannot_touch_other_registrations(self, world):
        world.as_user(world.bob).create_registration(1, 1)
        ana = world.as_user(world.ana)
        with pytest.raises(PermissionError, match=Msg.CUSTOMER_OWN_ONLY):
            ana.cancel_registration(1)
        with pytest.raises(PermissionError):
            ana.update_registration(1, event_id=1)
        assert len(world.data.get_registrations()) == 1

    def test_can_cancel_own_registration(self, world):
        ana = world.as_user(world.ana)
        ana.create_registration(1, 1)
        ana.cancel_registration(1)
        assert world.data.get_registrations() == []


# ---------------- missing resources ----------------

@pytest.mark.parametrize("lookup, message", [
    (lambda d: d.get_user(42), Msg.USER_NOT_FOUND.format(id=42)),
    (lambda d: d.get_event(42), Msg.EVENT_NOT_FOUND.format(id=42)),
    (lambda d: d.get_registration(42), Msg.REGISTRATION_NOT_FOUND.format(id=42)),
])
def test_missing_resources_raise_key_error(world, lookup, message):
    with pytest.raises(KeyError) as error:
        lookup(world.data)
    assert error.value.args[0] == message


def test_messages_are_formatted():
    assert Msg.EVENT_NOT_FOUND.format(id=3) == "Event 3 not found"
    assert Msg.CANNOT.format(type="Customer", action=Msg.ACTION_ADD_EVENTS) == "Customer cannot add events"


# ---------------- JSON storage ----------------

class TestJsonStorage:
    def test_round_trip(self, world, tmp_path):
        world.as_user(world.manager).create_registration(1, 1, world.ana.id)
        storage = JsonStorage(str(tmp_path))
        storage.save(world.data)

        loaded = JsonStorage(str(tmp_path)).load()
        assert isinstance(loaded.get_user(1), Manager)
        assert isinstance(loaded.get_user(2), Customer)
        assert loaded.get_user(2).check_password("ana123")
        event = loaded.get_event(1)
        assert (event.name, event.capacity) == ("Concert", 2)
        registration = loaded.get_registration(1)
        assert (registration.eventId, registration.userId, registration.userName) == (1, 2, "Ana")

    def test_session(self, tmp_path):
        storage = JsonStorage(str(tmp_path))
        assert storage.load_session() is None
        storage.save_session(5)
        assert storage.load_session() == 5
        storage.clear_session()
        assert storage.load_session() is None

    def test_empty_directory_loads_empty_data(self, tmp_path):
        data = JsonStorage(str(tmp_path)).load()
        assert data.users == {} and data.get_events() == [] and data.get_registrations() == []

    def test_data_still_loads_after_removing_event_with_registrations(self, world, tmp_path):
        manager = world.as_user(world.manager)
        manager.create_registration(1, 1, world.ana.id)
        manager.remove_event(1)
        JsonStorage(str(tmp_path)).save(world.data)
        loaded = JsonStorage(str(tmp_path)).load()  # used to fail with "Event 1 not found"
        assert loaded.get_events() == [] and loaded.get_registrations() == []
