import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("DB_HOST", None)  # always use JSON storage in tests

from api import create_app  # noqa: E402
from Localizable import Api, ErrorCode, Role  # noqa: E402


@pytest.fixture
def client(tmp_path):
    app = create_app({"DATA_DIR": str(tmp_path), "TESTING": True})
    return app.test_client()


def login(client, role, name, password="pw"):
    res = client.post("/api/v1/sessions", json={"role": role, "name": name, "password": password})
    assert res.status_code == 201, res.json
    return {"Authorization": f"Bearer {res.json['token']}"}


def test_login_validation_and_credentials(client):
    assert client.post("/api/v1/sessions", data="x").status_code == 400
    res = client.post("/api/v1/sessions", json={"role": "admin", "name": "a", "password": "b"})
    assert res.status_code == 400 and res.json["error"]["code"] == ErrorCode.VALIDATION
    login(client, Role.MANAGER, "Luis", "luis123")
    res = client.post("/api/v1/sessions", json={"role": Role.MANAGER, "name": "Luis", "password": "bad"})
    assert res.status_code == 401


def test_auth_required_and_logout(client):
    assert client.get("/api/v1/events").status_code == 401
    assert client.get("/api/v1/events", headers={"Authorization": "Bearer junk"}).status_code == 401
    h = login(client, Role.CUSTOMER, "Ana")
    me = client.get("/api/v1/users/me", headers=h)
    assert me.status_code == 200 and me.json["role"] == Role.CUSTOMER
    assert client.delete("/api/v1/sessions/current", headers=h).status_code == 204
    assert client.get("/api/v1/users/me", headers=h).status_code == 401


def test_event_crud(client):
    m = login(client, Role.MANAGER, "Luis")
    res = client.post("/api/v1/events", json={"name": "Concert", "capacity": 2}, headers=m)
    assert res.status_code == 201
    assert res.headers["Location"].endswith("/api/v1/events/1")
    assert res.json == {"id": 1, "name": "Concert", "capacity": 2, "availablePlaces": 2}

    assert client.post("/api/v1/events", json={"name": "X", "capacity": 0}, headers=m).status_code == 400
    assert client.post("/api/v1/events", json={"name": "X", "capacity": "2"}, headers=m).status_code == 400
    assert client.get("/api/v1/events/1", headers=m).status_code == 200
    assert client.get("/api/v1/events/99", headers=m).status_code == 404

    res = client.patch("/api/v1/events/1", json={"capacity": 5}, headers=m)
    assert res.status_code == 200 and res.json["capacity"] == 5 and res.json["name"] == "Concert"
    assert client.patch("/api/v1/events/99", json={"capacity": 5}, headers=m).status_code == 404

    assert len(client.get("/api/v1/events?minAvailablePlaces=5", headers=m).json) == 1
    assert len(client.get("/api/v1/events?minAvailablePlaces=6", headers=m).json) == 0
    assert client.get("/api/v1/events?minAvailablePlaces=x", headers=m).status_code == 400

    assert client.delete("/api/v1/events/1", headers=m).status_code == 204
    assert client.delete("/api/v1/events/1", headers=m).status_code == 404


def test_customer_cannot_manage_events(client):
    c = login(client, Role.CUSTOMER, "Ana")
    res = client.post("/api/v1/events", json={"name": "X", "capacity": 3}, headers=c)
    assert res.status_code == 403 and res.json["error"]["code"] == ErrorCode.FORBIDDEN


def test_registrations_flow(client):
    m = login(client, Role.MANAGER, "Luis")
    client.post("/api/v1/events", json={"name": "Concert", "capacity": 1}, headers=m)
    client.post("/api/v1/events", json={"name": "Hike", "capacity": 3}, headers=m)
    c = login(client, Role.CUSTOMER, "Ana")

    res = client.post("/api/v1/registrations", json={"eventId": 1}, headers=c)
    assert res.status_code == 201 and res.json["userName"] == "Ana"
    assert res.headers["Location"].endswith("/api/v1/registrations/1")

    # Event 1 is full now
    res = client.post("/api/v1/registrations", json={"eventId": 1, "attendee": "Bob"}, headers=m)
    assert res.status_code == 409 and res.json["error"]["code"] == ErrorCode.EVENT_FULL
    assert client.post("/api/v1/registrations", json={"eventId": 99}, headers=c).status_code == 404
    assert client.post("/api/v1/registrations", json={}, headers=c).status_code == 400
    # customers cannot register other people
    assert client.post("/api/v1/registrations", json={"eventId": 2, "attendee": "Zed"}, headers=c).status_code == 403

    # manager registers someone else (created on the fly)
    res = client.post("/api/v1/registrations", json={"eventId": 2, "attendee": "Bob"}, headers=m)
    assert res.status_code == 201
    bob_reg = res.json["id"]

    assert len(client.get("/api/v1/registrations", headers=m).json) == 2
    assert len(client.get("/api/v1/registrations", headers=c).json) == 1
    assert client.get(f"/api/v1/registrations/{bob_reg}", headers=c).status_code == 403
    assert client.get("/api/v1/registrations/99", headers=c).status_code == 404

    res = client.patch(f"/api/v1/registrations/{bob_reg}", json={"attendee": "Marco"}, headers=m)
    assert res.status_code == 200 and res.json["userName"] == "Marco"
    assert client.delete(f"/api/v1/registrations/{bob_reg}", headers=c).status_code == 403
    assert client.delete(f"/api/v1/registrations/{bob_reg}", headers=m).status_code == 204
    assert client.delete("/api/v1/registrations/1", headers=c).status_code == 204


def test_static_pages(client):
    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200
    res = client.get("/openapi.yaml")
    assert res.status_code == 200 and b"openapi: 3.1.0" in res.data


def test_openapi_spec_is_valid():
    validator = pytest.importorskip("openapi_spec_validator")
    import yaml

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "openapi.yaml"), encoding="utf-8") as f:
        validator.validate(yaml.safe_load(f))


def test_delete_event_with_registrations(client):
    m = login(client, Role.MANAGER, "Luis")
    client.post("/api/v1/events", json={"name": "Concert", "capacity": 5}, headers=m)
    client.post("/api/v1/registrations", json={"eventId": 1, "attendee": "Ana"}, headers=m)
    assert client.delete("/api/v1/events/1", headers=m).status_code == 204
    # data must still load afterwards and the registration is gone
    assert client.get("/api/v1/registrations", headers=m).json == []
    assert client.get("/api/v1/events", headers=m).json == []
