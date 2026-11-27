import importlib
import pkgutil
from datetime import date, timedelta

import pytest
import typer

import bakelib
from bake import Context
from bake.ui.logger import strip_ansi
from bakelib import (
    BaseSpace,
    GitHubActionsTools,
    Migration,
    PythonSpace,
    assert_no_expired_migrations,
)


def migration(expires: date, description: str = "Remove old-tool from mise.toml") -> Migration:
    class DatedMigration(Migration):
        def check(self, ctx: Context) -> bool:
            _ = ctx
            return False

        def apply(self, ctx: Context) -> None:
            _ = ctx

    dated = DatedMigration()
    dated.expires = expires
    dated.description = description
    return dated


def space_with(migrations: dict[str, Migration]) -> BaseSpace:
    class MigratingSpace(BaseSpace):
        def _get_migrations(self) -> dict[str, Migration]:
            return {**super()._get_migrations(), **migrations}

    return MigratingSpace()


def test_passes_for_future_and_today() -> None:
    today = date.today()
    bakebook = space_with(
        {
            "future": migration(today + timedelta(days=90)),
            "today": migration(today),
        }
    )

    assert_no_expired_migrations(bakebook)


def test_passes_without_migrations() -> None:
    assert_no_expired_migrations(BaseSpace())


def test_fails_naming_the_expired_migration() -> None:
    yesterday = date.today() - timedelta(days=1)
    bakebook = space_with(
        {
            "unuse-old-tool": migration(yesterday, "Remove old-tool from mise.toml"),
            "future": migration(date.today() + timedelta(days=1)),
        }
    )

    with pytest.raises(AssertionError) as exc_info:
        assert_no_expired_migrations(bakebook)

    message = str(exc_info.value)
    assert "unuse-old-tool" in message
    assert "Remove old-tool from mise.toml" in message
    assert yesterday.isoformat() in message
    assert "future" not in message


def test_fails_naming_every_expired_migration() -> None:
    bakebook = space_with(
        {
            "drop-a": migration(date(2020, 1, 1), "Drop a"),
            "drop-b": migration(date(2021, 6, 30), "Drop b"),
        }
    )

    with pytest.raises(AssertionError) as exc_info:
        assert_no_expired_migrations(bakebook)

    message = str(exc_info.value)
    assert "drop-a" in message
    assert "Drop a" in message
    assert "2020-01-01" in message
    assert "drop-b" in message
    assert "Drop b" in message
    assert "2021-06-30" in message


def test_dead_opt_out_exits_2_with_delete_that_line_message(
    capsys: pytest.CaptureFixture,
) -> None:
    class DeadOptOutSpace(BaseSpace):
        def _get_migrations(self) -> dict[str, Migration]:
            migrations = super()._get_migrations()
            del migrations["gone-upstream"]
            return migrations

    with pytest.raises(typer.Exit) as exc_info:
        assert_no_expired_migrations(DeadOptOutSpace())

    assert exc_info.value.exit_code == 2
    err = strip_ansi(capsys.readouterr().err)
    assert "'gone-upstream'" in err
    assert "delete that line" in err


def _bakelib_spaces() -> list[type[BaseSpace]]:
    for module in pkgutil.walk_packages(bakelib.__path__, "bakelib."):
        if not module.name.endswith(".__main__"):
            importlib.import_module(module.name)
    found: list[type[BaseSpace]] = []
    pending: list[type[BaseSpace]] = [BaseSpace]
    while pending:
        space_cls = pending.pop()
        pending.extend(space_cls.__subclasses__())
        if space_cls.__module__.startswith("bakelib.") and space_cls not in found:
            found.append(space_cls)
    return found


def _bakebook_of(space_cls: type[BaseSpace]) -> BaseSpace:
    stubs = {name: lambda *_, **__: None for name in space_cls.__abstractmethods__}
    concrete = type(f"Concrete{space_cls.__name__}", (space_cls,), stubs)
    # skips construction, where some Spaces require project fields such as a DVC remote
    bakebook = concrete.__new__(concrete)
    defaults = {
        name: info.get_default(call_default_factory=True)
        for name, info in concrete.model_fields.items()
    }
    object.__setattr__(bakebook, "__dict__", defaults)
    return bakebook


BAKELIB_SPACES = _bakelib_spaces()


def test_bakelib_spaces_are_found() -> None:
    assert {BaseSpace, PythonSpace, GitHubActionsTools} <= set(BAKELIB_SPACES)


@pytest.mark.parametrize("space_cls", BAKELIB_SPACES, ids=lambda cls: cls.__name__)
def test_bakelib_space_has_no_expired_migrations(space_cls: type[BaseSpace]) -> None:
    assert_no_expired_migrations(_bakebook_of(space_cls))
