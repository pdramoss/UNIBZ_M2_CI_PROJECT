from User import User
from Event import Event


class Registration:
    def __init__(self, id: int, user: User, event: Event):
        self.id = id
        self.eventId = event.id
        self.userId = user.id
        self.userName = user.name
