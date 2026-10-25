from User import User


class Manager(User):
    def __init__(self, id: int, name: str, age: int, id_event: int):
        super().__init__(id, name, age)
        self.id_event = id_event
