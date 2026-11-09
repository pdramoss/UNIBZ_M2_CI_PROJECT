"""REST API for the events/registrations application.

Resources:  /api/v1/sessions, /api/v1/users/me, /api/v1/events, /api/v1/registrations
Docs:       /openapi.yaml (OpenAPI 3.1 spec), /docs (Swagger UI), / (web form)
Run:        flask --app api run   (or: python api.py)
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(BASE_DIR, folder) for folder in ("Models", "States", "Storage")] + [BASE_DIR]

from functools import wraps

from flask import Flask, g, jsonify, request, send_from_directory, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.exceptions import HTTPException

from Adapter import Adapter
from Event import Event
from Registration import Registration
from StorageFactory import create_storage
from UserState import EventFullError
from Services import available_places, login_user, next_id, resolve_attendee
from Localizable import Api, Defaults, Env, ErrorCode, Field, Msg, Role


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


# ---------- JSON representations ----------

def user_json(user) -> dict:
    return {Field.ID: user.id, Field.NAME: user.name, Field.ROLE: type(user).__name__.lower(), Field.AGE: user.age}


def event_json(data_source, event: Event) -> dict:
    return {
        Field.ID: event.id,
        Field.NAME: event.name,
        Field.CAPACITY: event.capacity,
        Field.AVAILABLE_PLACES: available_places(data_source, event),
    }


def registration_json(registration: Registration) -> dict:
    return {
        Field.ID: registration.id,
        Field.EVENT_ID: registration.eventId,
        Field.USER_ID: registration.userId,
        Field.USER_NAME: registration.userName,
    }


# ---------- request validation ----------

def json_body() -> dict:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError(400, ErrorCode.INVALID_BODY, Msg.BODY_NOT_OBJECT)
    return body


def field(body: dict, name: str, kind: type, required: bool = True, minimum: int | None = None):
    if name not in body or body[name] is None:
        if required:
            raise ApiError(400, ErrorCode.VALIDATION, Msg.FIELD_REQUIRED.format(name=name))
        return None
    value = body[name]
    # bool is a subclass of int; reject it explicitly
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise ApiError(400, ErrorCode.VALIDATION, Msg.FIELD_TYPE.format(name=name, type=kind.__name__))
    if kind is str and not value.strip():
        raise ApiError(400, ErrorCode.VALIDATION, Msg.FIELD_EMPTY.format(name=name))
    if minimum is not None and value < minimum:
        raise ApiError(400, ErrorCode.VALIDATION, Msg.FIELD_MIN.format(name=name, minimum=minimum))
    return value


# ---------- application ----------

def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=os.path.join(BASE_DIR, Api.STATIC_DIR), static_url_path="/" + Api.STATIC_DIR)
    app.config["SECRET_KEY"] = os.environ.get(Env.API_SECRET_KEY, Defaults.DEV_SECRET)
    app.config["DATA_DIR"] = BASE_DIR
    app.config.update(config or {})
    serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"], salt=Api.TOKEN_SALT)
    revoked: set[str] = set()

    # ----- errors: every error is {"error": {"code", "message"}} -----

    def error(status: int, code: str, message: str):
        return jsonify({Field.ERROR: {Field.CODE: code, Field.MESSAGE: message}}), status

    @app.errorhandler(ApiError)
    def handle_api_error(e: ApiError):
        return error(e.status, e.code, e.message)

    @app.errorhandler(KeyError)
    def handle_not_found(e: KeyError):
        return error(404, ErrorCode.NOT_FOUND, str(e.args[0]) if e.args else Msg.RESOURCE_NOT_FOUND)

    @app.errorhandler(PermissionError)
    def handle_forbidden(e: PermissionError):
        return error(403, ErrorCode.FORBIDDEN, str(e))

    @app.errorhandler(EventFullError)
    def handle_full(e: EventFullError):
        return error(409, ErrorCode.EVENT_FULL, str(e))

    @app.errorhandler(ValueError)
    def handle_invalid(e: ValueError):
        return error(400, ErrorCode.VALIDATION, str(e))

    @app.errorhandler(HTTPException)
    def handle_http(e: HTTPException):
        return error(e.code, e.name.lower().replace(" ", "_"), e.description)

    # ----- per-request data access -----

    def storage():
        return create_storage(app.config["DATA_DIR"])

    def load():
        g.storage = storage()
        g.data = g.storage.load()
        return g.data

    def save():
        g.storage.save(g.data)

    @app.teardown_request
    def close_storage(_exc):
        storage_in_use = g.pop("storage", None)
        if storage_in_use is not None:
            storage_in_use.close()

    def authenticated(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            header = request.headers.get(Api.AUTH_HEADER, "")
            if not header.startswith(Api.BEARER):
                raise ApiError(401, ErrorCode.UNAUTHORIZED, Msg.MISSING_TOKEN)
            token = header[len(Api.BEARER):]
            try:
                user_id = serializer.loads(token, max_age=Defaults.TOKEN_MAX_AGE)
            except (BadSignature, SignatureExpired):
                raise ApiError(401, ErrorCode.UNAUTHORIZED, Msg.INVALID_TOKEN)
            data = load()
            if token in revoked or user_id not in data.users:
                raise ApiError(401, ErrorCode.UNAUTHORIZED, Msg.INVALID_TOKEN)
            g.token = token
            g.adapter = Adapter(data)
            g.adapter.login(data.get_user(user_id))
            return view(*args, **kwargs)
        return wrapper

    def created(payload: dict, location: str):
        response = jsonify(payload)
        response.status_code = 201
        response.headers[Api.LOCATION_HEADER] = location
        return response

    # ----- web form and docs -----

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, Api.INDEX_PAGE)

    @app.get("/" + Api.SPEC_FILE)
    def openapi_spec():
        return send_from_directory(BASE_DIR, Api.SPEC_FILE, mimetype=Api.YAML_MIMETYPE)

    @app.get("/docs")
    def docs():
        return send_from_directory(app.static_folder, Api.DOCS_PAGE)

    # ----- sessions -----

    @app.post(Api.PREFIX + "/sessions")
    def create_session():
        body = json_body()
        role = field(body, Field.ROLE, str)
        if role not in Role.ALL:
            raise ApiError(400, ErrorCode.VALIDATION, Msg.ROLE_INVALID)
        name = field(body, Field.NAME, str)
        password = field(body, Field.PASSWORD, str)
        age = field(body, Field.AGE, int, required=False, minimum=Defaults.MIN_AGE) or Defaults.MIN_AGE
        data = load()
        try:
            user = login_user(data, role, name.strip(), password, age)
        except PermissionError as e:
            raise ApiError(401, ErrorCode.INVALID_CREDENTIALS, str(e))
        save()
        return created({Field.TOKEN: serializer.dumps(user.id), Field.USER: user_json(user)},
                       url_for("current_user"))

    @app.delete(Api.PREFIX + "/sessions/current")
    @authenticated
    def delete_session():
        revoked.add(g.token)
        return "", 204

    @app.get(Api.PREFIX + "/users/me")
    @authenticated
    def current_user():
        return jsonify(user_json(g.adapter.state.user))

    # ----- events -----

    @app.get(Api.PREFIX + "/events")
    @authenticated
    def list_events():
        minimum = request.args.get(Field.MIN_AVAILABLE_PLACES)
        events = g.adapter.view_events()
        if minimum is not None:
            try:
                minimum = int(minimum)
            except ValueError:
                raise ApiError(400, ErrorCode.VALIDATION, Msg.QUERY_INT.format(name=Field.MIN_AVAILABLE_PLACES))
            events = [e for e in events if available_places(g.data, e) >= minimum]
        return jsonify([event_json(g.data, e) for e in events])

    @app.post(Api.PREFIX + "/events")
    @authenticated
    def create_event():
        body = json_body()
        name = field(body, Field.NAME, str).strip()
        capacity = field(body, Field.CAPACITY, int, minimum=Defaults.MIN_CAPACITY)
        event = Event(next_id(g.data.events), name, capacity)
        g.adapter.add_event(event)
        save()
        return created(event_json(g.data, event), url_for("get_event", event_id=event.id))

    @app.get(Api.PREFIX + "/events/<int:event_id>")
    @authenticated
    def get_event(event_id: int):
        g.adapter.view_events()  # permission check
        return jsonify(event_json(g.data, g.data.get_event(event_id)))

    @app.patch(Api.PREFIX + "/events/<int:event_id>")
    @authenticated
    def update_event(event_id: int):
        body = json_body()
        name = field(body, Field.NAME, str, required=False)
        capacity = field(body, Field.CAPACITY, int, required=False, minimum=Defaults.MIN_CAPACITY)
        current = g.data.get_event(event_id)
        g.adapter.update_event(event_id,
                               current.name if name is None else name.strip(),
                               current.capacity if capacity is None else capacity)
        save()
        return jsonify(event_json(g.data, g.data.get_event(event_id)))

    @app.delete(Api.PREFIX + "/events/<int:event_id>")
    @authenticated
    def delete_event(event_id: int):
        g.adapter.remove_event(event_id)
        save()
        return "", 204

    # ----- registrations -----

    @app.get(Api.PREFIX + "/registrations")
    @authenticated
    def list_registrations():
        return jsonify([registration_json(r) for r in g.adapter.view_registrations()])

    @app.post(Api.PREFIX + "/registrations")
    @authenticated
    def create_registration():
        body = json_body()
        event_id = field(body, Field.EVENT_ID, int, minimum=Defaults.MIN_ID)
        attendee = field(body, Field.ATTENDEE, str, required=False)
        user_id = None if attendee is None else resolve_attendee(g.adapter, g.data, attendee.strip())
        registration = g.adapter.create_registration(next_id(g.data.registrations), event_id, user_id)
        save()
        return created(registration_json(registration),
                       url_for("get_registration", registration_id=registration.id))

    @app.get(Api.PREFIX + "/registrations/<int:registration_id>")
    @authenticated
    def get_registration(registration_id: int):
        visible = {r.id: r for r in g.adapter.view_registrations()}
        if registration_id not in visible:
            g.data.get_registration(registration_id)  # 404 if it does not exist at all
            raise PermissionError(Msg.VIEW_OWN_ONLY)
        return jsonify(registration_json(visible[registration_id]))

    @app.patch(Api.PREFIX + "/registrations/<int:registration_id>")
    @authenticated
    def update_registration(registration_id: int):
        body = json_body()
        attendee = field(body, Field.ATTENDEE, str, required=False)
        event_id = field(body, Field.EVENT_ID, int, required=False, minimum=Defaults.MIN_ID)
        user_id = None if attendee is None else resolve_attendee(g.adapter, g.data, attendee.strip())
        registration = g.adapter.update_registration(registration_id, event_id, user_id)
        save()
        return jsonify(registration_json(registration))

    @app.delete(Api.PREFIX + "/registrations/<int:registration_id>")
    @authenticated
    def delete_registration(registration_id: int):
        g.adapter.cancel_registration(registration_id)
        save()
        return "", 204

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host=Defaults.API_HOST, port=int(os.environ.get(Env.PORT, Defaults.API_PORT)))
