from User import User


class Customer(User):
    def __init__(self, id: int, name: str, age: int, id_registration: int):
        super().__init__(id, name, age)
        self.id_registration = id_registration
