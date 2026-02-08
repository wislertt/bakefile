import inspect
import types
from pathlib import Path

import click
import pytest
import typer
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, Context, command
from bake.utils.constants import BAKE_COMMAND_KWARGS
from bake.utils.exceptions import ContextNotAvailableError
from tests.unit.bake.bakebook.utils import (
    ExpectedCommand,
    assert_commands,
    assert_signature_matches_typer,
)


def test_bakebook_command_signature_matches_typer() -> None:
    """Ensure Bakebook.command() signature matches Typer's Typer.command()."""
    assert_signature_matches_typer(inspect.signature(Bakebook.command), "Bakebook.command")


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

    assert_commands(
        bakebook,
        {
            "test_method": ExpectedCommand(
                name="test_method", command_type=types.MethodType, output="test"
            ),
            "test_cmd": ExpectedCommand(
                name="test_cmd", command_type=types.FunctionType, output=None
            ),
        },
        msg="MyBakebook with method and function commands",
    )


def test_inheritance() -> None:
    class ParentBakebook(Bakebook):
        @command()
        def parent_method(self):
            return "parent"

    class ChildBakebook(ParentBakebook):
        @command()
        def parent_method(self):
            return "child"

    child = ChildBakebook()

    @child.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    assert_commands(
        child,
        {
            "parent_method": ExpectedCommand(
                name="parent_method", command_type=types.MethodType, output="child"
            ),
            "test_cmd": ExpectedCommand(
                name="test_cmd", command_type=types.FunctionType, output=None
            ),
        },
        msg="ChildBakebook with overridden parent method",
    )


def test_inheritance_without_decorator() -> None:
    class ParentBakebook(Bakebook):
        @command()
        def parent_method(self):
            return "parent"

    class ChildBakebook(ParentBakebook):
        # child method override parent without decorator - inherits parent's command registration
        def parent_method(self):
            return "child"

    child = ChildBakebook()

    @child.command()
    def test_cmd(name: str = "default"):
        """Test command."""

    # Both test_cmd and parent_method are registered - parent_method override
    # without @command now inherits the parent's command registration
    assert_commands(
        child,
        {
            "parent_method": ExpectedCommand(
                name="parent_method", command_type=types.MethodType, output="child"
            ),
            "test_cmd": ExpectedCommand(
                name="test_cmd", command_type=types.FunctionType, output=None
            ),
        },
        msg="ChildBakebook inherits parent's command registration",
    )


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


class TestBakebookCtxProperty:
    def test_ctx_raises_when_no_click_context(self) -> None:
        bakebook = Bakebook()

        with pytest.raises(ContextNotAvailableError, match="Command context not available"):
            _ = bakebook.ctx

    def test_ctx_raises_when_wrong_context_type(self) -> None:
        bakebook = Bakebook()

        # Create a plain click.Context (not bake.Context)
        plain_ctx = click.Context(command=click.Command("test"))

        expected_msg = (
            r"Expected <class 'bake\.cli\.common\.context\.Context'>, "
            r"got <class 'click\.core\.Context'>"
        )
        with plain_ctx, pytest.raises(ContextNotAvailableError, match=expected_msg):
            _ = bakebook.ctx

    def test_ctx_returns_context_when_available(self, mock_ctx: Context) -> None:
        bakebook = Bakebook()

        with mock_ctx:
            result = bakebook.ctx
            assert result is mock_ctx
            assert isinstance(result, Context)

    def test_ctx_parameter_injection_matches_self_ctx(self, mock_ctx: Context) -> None:
        """Verify that Typer's context injection matches self.ctx.

        When a command method has `ctx: Context` as a parameter, Typer injects
        the Click context. This test simulates what happens when Typer calls
        a command method and verifies the injected ctx matches self.ctx.
        """
        # TODO: !!!

        # Create a dummy Bakebook with a command that uses ctx parameter
        class TestBakebook(Bakebook):
            injected_ctx: Context | None = None
            self_ctx: Context | None = None

            @command()
            def test_cmd(self, ctx: Context) -> None:
                # Capture both the injected ctx and self.ctx
                self.injected_ctx = ctx
                self.self_ctx = self.ctx

        bakebook = TestBakebook()

        # Simulate what Typer does when calling a command:
        # 1. Click context is made available via click.get_current_context()
        # 2. Typer injects that context as the ctx parameter
        # This is exactly what happens when bake commands are invoked
        with mock_ctx:
            bakebook.test_cmd(mock_ctx)

        # Verify both are the same object (mock_ctx)
        assert bakebook.injected_ctx is mock_ctx
        assert bakebook.self_ctx is mock_ctx
        # Most importantly: the injected ctx IS self.ctx
        assert bakebook.injected_ctx is bakebook.self_ctx
