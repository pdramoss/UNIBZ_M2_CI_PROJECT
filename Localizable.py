"""Global strings and constants of the application (no magic values in the code).

Messages are templates: use them with ``.format(...)``, e.g. ``Msg.EVENT_NOT_FOUND.format(id=3)``.
"""


class Role:
    MANAGER = "manager"
    CUSTOMER = "customer"
    ALL = (MANAGER, CUSTOMER)


class Env:
    DB_HOST = "DB_HOST"
    DB_PORT = "DB_PORT"
    DB_NAME = "DB_NAME"
    DB_USER = "DB_USER"
    DB_PASSWORD = "DB_PASSWORD"
    EVENTS_DATA_DIR = "EVENTS_DATA_DIR"
    API_SECRET_KEY = "API_SECRET_KEY"
    PORT = "PORT"


class Defaults:
    DB_PORT = 3306
    API_HOST = "0.0.0.0"
    API_PORT = 8000
    TOKEN_MAX_AGE = 8 * 60 * 60  # seconds
    DEV_SECRET = "dev-secret-change-me"
    MIN_CAPACITY = 1
    MIN_ID = 1
    MIN_AGE = 0
    DATA_FILE = "data.json"
    SESSION_FILE = "session.json"


class Api:
    PREFIX = "/api/v1"
    AUTH_HEADER = "Authorization"
    BEARER = "Bearer "
    TOKEN_SALT = "session"
    LOCATION_HEADER = "Location"
    YAML_MIMETYPE = "application/yaml"
    SPEC_FILE = "openapi.yaml"
    INDEX_PAGE = "index.html"
    DOCS_PAGE = "docs.html"
    STATIC_DIR = "static"


class Field:
    ROLE = "role"
    NAME = "name"
    PASSWORD = "password"
    AGE = "age"
    CAPACITY = "capacity"
    EVENT_ID = "eventId"
    ATTENDEE = "attendee"
    AVAILABLE_PLACES = "availablePlaces"
    MIN_AVAILABLE_PLACES = "minAvailablePlaces"
    ID = "id"
    USER_ID = "userId"
    USER_NAME = "userName"
    TOKEN = "token"
    USER = "user"
    ERROR = "error"
    CODE = "code"
    MESSAGE = "message"


class ErrorCode:
    INVALID_BODY = "invalid_body"
    VALIDATION = "validation_error"
    UNAUTHORIZED = "unauthorized"
    INVALID_CREDENTIALS = "invalid_credentials"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    EVENT_FULL = "event_full"


class Msg:
    # Domain
    USER_NOT_FOUND = "User {id} not found"
    EVENT_NOT_FOUND = "Event {id} not found"
    REGISTRATION_NOT_FOUND = "Registration {id} not found"
    EVENT_FULL = "Event {id} is full"
    INVALID_PASSWORD = "Invalid password"
    UNKNOWN_ROLE = "Unknown role '{role}'"
    NO_STATE = "No state defined for {type}"
    NO_USER_LOGGED_IN = "No user logged in"
    CANNOT = "{type} cannot {action}"
    CUSTOMER_SELF_ONLY = "Customer can only register themselves"
    CUSTOMER_OWN_ONLY = "Customer can only manage their own registrations"
    VIEW_OWN_ONLY = "You can only view your own registrations"

    # Actions used in Msg.CANNOT
    ACTION_VIEW_EVENTS = "view events"
    ACTION_CREATE_USERS = "create users"
    ACTION_CREATE_REGISTRATIONS = "create registrations"
    ACTION_UPDATE_REGISTRATIONS = "update registrations"
    ACTION_VIEW_REGISTRATIONS = "view registrations"
    ACTION_CANCEL_REGISTRATIONS = "cancel registrations"
    ACTION_ADD_EVENTS = "add events"
    ACTION_UPDATE_EVENTS = "update events"
    ACTION_REMOVE_EVENTS = "remove events"

    # CLI output
    LOGGED_IN = "Logged in as {type} {name} (id {id})"
    LOGGED_OUT = "Logged out"
    WHOAMI = "{type} {name} (id {id})"
    EVENT_CREATED = "Event {id} created"
    EVENT_UPDATED = "Event {id} updated"
    EVENT_REMOVED = "Event {id} removed"
    REGISTRATION_CREATED = "Registration {id} created"
    REGISTRATION_UPDATED = "Registration {id} updated"
    REGISTRATION_CANCELLED = "Registration {id} cancelled"
    EVENT_LINE = "[{id}] {name} - capacity {capacity}, available {available}"
    REGISTRATION_LINE = "[{id}] event {event_id} - {user_name} (user {user_id})"
    ERROR = "Error: {error}"
    DATABASE_ERROR = "Error: database error ({error})"

    # API validation / auth
    BODY_NOT_OBJECT = "Request body must be a JSON object"
    FIELD_REQUIRED = "Field '{name}' is required"
    FIELD_TYPE = "Field '{name}' must be of type {type}"
    FIELD_EMPTY = "Field '{name}' must not be empty"
    FIELD_MIN = "Field '{name}' must be >= {minimum}"
    ROLE_INVALID = "Field 'role' must be 'manager' or 'customer'"
    QUERY_INT = "Query parameter '{name}' must be an integer"
    MISSING_TOKEN = "Missing bearer token"
    INVALID_TOKEN = "Invalid or expired token"
    RESOURCE_NOT_FOUND = "Resource not found"
