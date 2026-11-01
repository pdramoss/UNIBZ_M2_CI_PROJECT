import hashlib
import hmac
import secrets


class User:
    def __init__(self, id: int, name: str, age: int, password: str | None = None):
        self.id = id
        self.name = name
        self.age = age
        # Stored as "salt$sha256hex", never as plain text
        self.password: str | None = None
        if password is not None:
            self.set_password(password)

    @staticmethod
    def hash_password(password: str, salt: str | None = None) -> str:
        salt = secrets.token_hex(16) if salt is None else salt
        digest = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
        return f"{salt}${digest}"

    def set_password(self, password: str):
        self.password = self.hash_password(password)

    def check_password(self, password: str) -> bool:
        if self.password is None:
            return False
        salt, _ = self.password.split("$", 1)
        return hmac.compare_digest(self.hash_password(password, salt), self.password)
