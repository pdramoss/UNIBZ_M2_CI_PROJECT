from abc import ABC, abstractmethod

from DataSource import DataSource


class BaseStorage(ABC):
    @abstractmethod
    def load(self) -> DataSource: ...

    @abstractmethod
    def save(self, data_source: DataSource): ...

    @abstractmethod
    def load_session(self) -> int | None: ...

    @abstractmethod
    def save_session(self, user_id: int): ...

    @abstractmethod
    def clear_session(self): ...
