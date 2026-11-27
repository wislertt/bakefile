from abc import ABC, abstractmethod
from datetime import date

from bake import Context


class Migration(ABC):
    expires: date
    description: str

    @abstractmethod
    def check(self, ctx: Context) -> bool: ...

    @abstractmethod
    def apply(self, ctx: Context) -> None: ...
