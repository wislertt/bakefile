from abc import ABC, abstractmethod
from datetime import date
from typing import TYPE_CHECKING

from bake import Context

if TYPE_CHECKING:
    from .base import BaseSpace


class Migration(ABC):
    expires: date
    description: str

    @abstractmethod
    def check(self, ctx: Context) -> bool: ...

    @abstractmethod
    def apply(self, ctx: Context) -> None: ...


def assert_no_expired_migrations(bakebook: "BaseSpace") -> None:
    today = date.today()
    expired = [
        f"Migration {key} expired on {migration.expires.isoformat()}: {migration.description}"
        for key, migration in bakebook.collect_migrations().items()
        if migration.expires < today
    ]
    if expired:
        raise AssertionError("\n".join([*expired, "remove each expired Migration"]))
