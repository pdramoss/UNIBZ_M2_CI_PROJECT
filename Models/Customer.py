from User import User


class Customer(User):
    def __init__(self, id: int, name: str, age: int, id_registration: int, password: str | None = None):
        super().__init__(id, name, age, password)
        self.id_registration = id_registration
