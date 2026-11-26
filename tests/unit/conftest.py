import keyring
import keyring.backend
import pytest

from bakelib.managed_content.testing import STAND_IN_GITIGNORE
from bakelib.space.base import BaseSpace


class _InMemoryKeyring(keyring.backend.KeyringBackend):
    priority = 99

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


@pytest.fixture(autouse=True)
def isolate_keyring_backend():
    # Unit tests must not touch the OS keychain: xdist workers race on shared entries
    original = keyring.get_keyring()
    keyring.set_keyring(_InMemoryKeyring())
    yield
    keyring.set_keyring(original)


@pytest.fixture(autouse=True)
def offline_gitignore_templates(monkeypatch: pytest.MonkeyPatch) -> None:
    # syncing a managed .gitignore fetches github/gitignore templates; unit tests stay offline
    monkeypatch.setattr(BaseSpace, "_get_gitignore_upstream", lambda _self: STAND_IN_GITIGNORE)
