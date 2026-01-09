import inspect
import types
from pathlib import Path

import pytest
import typer
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, command
from bake.utils.constants import BAKE_COMMAND_KWARGS
from tests.bake.bakebook.utils import _assert_signature_matches_typer


def test_bakebook_command_signature_matches_typer() -> None:
    """Ensure Bakebook.command() signature matches Typer's Typer.command()."""
    _assert_signature_matches_typer(inspect.signature(Bakebook.command), "Bakebook.command")


def test_create_empty_subclass() -> None:
    class MyBakebook(Bakebook):
        pass

    bakebook = MyBakebook()
    assert issubclass(MyBakebook, Bakebook)
    assert isinstance(bakebook, Bakebook)
    assert isinstance(bakebook._app, typer.Typer)
    assert "_app" not in bakebook.model_dump()


@pytest.mark.parametrize(
    "env_vars,init_kwargs,expected_url,expected_debug",
    [
        ({}, {}, "postgres://localhost", False),
        ({"DATABASE_URL": "postgres://prod", "DEBUG": "true"}, {}, "postgres://prod", True),
        (
            {"DATABASE_URL": "postgres://env"},
            {"database_url": "postgres://kwargs"},
            "postgres://kwargs",
            False,
        ),
    ],
    ids=["defaults", "from_env", "kwargs_override"],
)
def test_fields(
    monkeypatch: pytest.MonkeyPatch,
    env_vars: dict,
    init_kwargs: dict,
    expected_url: str,
    expected_debug: bool,
) -> None:
    class MyBakebook(Bakebook):
        database_url: str = "postgres://localhost"
        debug: bool = False

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    bakebook = MyBakebook(**init_kwargs)
    assert bakebook.database_url == expected_url
    assert bakebook.debug is expected_debug


def test_add_methods_to_subclass() -> None:
    class MyBakebook(Bakebook):
        api_key: str = ""

        def get_config(self) -> str:
            return f"key={self.api_key}"

    bakebook = MyBakebook(api_key="secret123")
    assert bakebook.get_config() == "key=secret123"


def test_command_registration() -> None:
    bakebook = Bakebook()

    assert len(bakebook._app.registered_commands) == 0

    @bakebook.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    assert isinstance(bakebook._app, typer.Typer)
    assert len(bakebook._app.registered_commands) > 0


@pytest.mark.parametrize(
    "env_file_content,env_vars,init_kwargs,expected_url,expected_debug",
    [
        (
            "DATABASE_URL=postgres://from_env_file\nDEBUG=true\n",
            {},
            {},
            "postgres://from_env_file",
            True,
        ),
        (
            "DATABASE_URL=from_env_file\n",
            {"DATABASE_URL": "from_env_var"},
            {"database_url": "from_kwargs"},
            "from_kwargs",
            False,
        ),
    ],
    ids=["env_file_loading", "priority"],
)
def test_base_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_file_content: str,
    env_vars: dict,
    init_kwargs: dict,
    expected_url: str,
    expected_debug: bool,
) -> None:
    class MyBakebook(Bakebook):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
        )
        database_url: str = "default://localhost"
        debug: bool = False

    env_file = tmp_path / ".env"
    env_file.write_text(env_file_content)

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    monkeypatch.chdir(tmp_path)

    bakebook = MyBakebook(**init_kwargs)
    assert bakebook.database_url == expected_url
    assert bakebook.debug is expected_debug


def test_method_command_registration() -> None:
    class MyBakebook(Bakebook):
        @command()
        def test_method(self):
            return "test"

    bakebook = MyBakebook()

    @bakebook.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    kwargs = object.__getattribute__(bakebook.test_method.__func__, BAKE_COMMAND_KWARGS)
    assert kwargs["name"] is None
    assert kwargs["help"] is None

    registered_commands = bakebook._app.registered_commands
    assert len(registered_commands) == 2
    method_1 = registered_commands[0].callback
    assert isinstance(method_1, types.MethodType)
    assert method_1.__name__ == "test_method"

    function_2 = registered_commands[1].callback
    assert isinstance(function_2, types.FunctionType)
    assert function_2.__name__ == "test_cmd"


def test_inheritance() -> None:
    class ParentBakebook(Bakebook):
        @command()
        def parent_method(self):
            return "parent"

    class ChildBakebook(ParentBakebook):
        # child method override parent method
        @command()
        def parent_method(self):
            return "child"

    child = ChildBakebook()

    @child.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    registered_commands = child._app.registered_commands
    assert len(registered_commands) == 2
    method_1 = registered_commands[0].callback
    assert isinstance(method_1, types.MethodType)
    assert method_1.__name__ == "parent_method"
    assert method_1() == "child"

    function_2 = registered_commands[1].callback
    assert isinstance(function_2, types.FunctionType)
    assert function_2.__name__ == "test_cmd"


def test_inheritance_without_decorator() -> None:
    class ParentBakebook(Bakebook):
        @command()
        def parent_method(self):
            return "parent"

    class ChildBakebook(ParentBakebook):
        # child method override parent without decorator and do not get registered
        def parent_method(self):
            return "child"

    child = ChildBakebook()

    @child.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    registered_commands = child._app.registered_commands
    assert len(registered_commands) == 1

    function_2 = registered_commands[0].callback
    assert isinstance(function_2, types.FunctionType)
    assert function_2.__name__ == "test_cmd"


def test_command_with_name_and_help() -> None:
    class MyBakebook(Bakebook):
        @command(name="build-release", help="Build the release package")
        def build(self):
            pass

    bakebook = MyBakebook()
    registered_commands = bakebook._app.registered_commands
    assert len(registered_commands) == 1

    command_info = registered_commands[0]
    assert command_info.name == "build-release"
    assert command_info.help == "Build the release package"
    assert isinstance(command_info.callback, types.MethodType)
    assert command_info.callback.__name__ == "build"
