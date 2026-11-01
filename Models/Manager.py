from User import User


class Manager(User):
    def __init__(self, id: int, name: str, age: int, id_event: int, password: str | None = None):
        super().__init__(id, name, age, password)
        self.id_event = id_event
