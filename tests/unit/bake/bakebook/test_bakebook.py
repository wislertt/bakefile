import inspect
import logging
import re
import types
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import click
import pytest
import typer
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, Context, command, parse_bake_log, serialize_bake_log
from bake.bakebook.bakebook import CommandKwargs, GroupKwargs
from bake.utils.constants import BAKE_COMMAND_KWARGS, DEFAULT_BAKE_LOG
from bake.utils.exceptions import ContextNotAvailableError
from tests.unit.bake.bakebook.utils import (
    ExpectedCommand,
    assert_commands,
    assert_signature_matches_typer,
)
from tests.utils.cli import CMD_BAKE, RunCli


def test_bakebook_command_signature_matches_typer() -> None:
    """Ensure Bakebook.command() signature matches Typer's Typer.command()."""
    assert_signature_matches_typer(inspect.signature(Bakebook.command), "Bakebook.command")


def test_command_kwargs_fields_match_command_decorator() -> None:
    """CommandKwargs fields should match @command decorator parameters."""
    decorator_sig = inspect.signature(command)
    decorator_params = list(decorator_sig.parameters.keys())

    # Get CommandKwargs fields (excluding methods)
    kwargs_fields = [f.name for f in CommandKwargs.__dataclass_fields__.values()]

    assert kwargs_fields == decorator_params, (
        f"CommandKwargs fields mismatch:\n"
        f"  CommandKwargs: {kwargs_fields}\n"
        f"  @command params: {decorator_params}"
    )

    # Verify defaults match
    for field_name in kwargs_fields:
        field = CommandKwargs.__dataclass_fields__[field_name]
        decorator_param = decorator_sig.parameters[field_name]

        # Handle Default wrapper for rich_help_panel
        kwargs_default = field.default
        decorator_default = decorator_param.default

        assert kwargs_default == decorator_default, (
            f"Default mismatch for '{field_name}': "
            f"CommandKwargs={kwargs_default!r}, @command={decorator_default!r}"
        )


def test_group_kwargs_fields_match_add_typer() -> None:
    """GroupKwargs fields should match Typer.add_typer() parameters (excluding name)."""
    add_typer_sig = inspect.signature(typer.Typer.add_typer)
    add_typer_params = list(add_typer_sig.parameters.keys())
    # Remove 'self', 'typer_instance', and 'name' (name is passed separately)
    add_typer_params = [p for p in add_typer_params if p not in ("self", "typer_instance", "name")]

    # Get GroupKwargs fields (excluding methods)
    kwargs_fields = [f.name for f in GroupKwargs.__dataclass_fields__.values()]

    assert kwargs_fields == add_typer_params, (
        f"GroupKwargs fields mismatch:\n"
        f"  GroupKwargs: {kwargs_fields}\n"
        f"  add_typer params (excl. name): {add_typer_params}"
    )


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
    assert isinstance(kwargs, CommandKwargs)
    assert kwargs.name is None
    assert kwargs.help is None

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

    def test_ctx_parameter_injection_matches_self_ctx(
        self, ctx_test_project: Path, run_cli: RunCli
    ) -> None:
        result = run_cli(
            command=CMD_BAKE,
            dir_path=ctx_test_project,
            args=["verify-ctx"],
        )

        assert result.exit_code == 0

        assert "SUCCESS - ctx matches self.ctx" in result.out

        # Extract both IDs and verify they're equal
        pattern = r"ctx_id: (\d+), self_ctx_id: (\d+)"
        match = re.search(pattern, result.out)
        assert match, f"Expected pattern not found in: {result.out}"
        ctx_id, self_ctx_id = match.groups()
        assert ctx_id == self_ctx_id


class TestSetupLogging:
    def test_setup_logging_configures_logging(self, capsys: pytest.CaptureFixture[str]) -> None:
        from bake.utils.settings import BakeSettings

        fresh_settings = BakeSettings()
        with patch("bake.bakebook.bakebook.bake_settings", fresh_settings):
            bb = Bakebook(bake_log="warning,bake=debug", bake_log_verbosity=3)
            bb.setup_logging()

            logging.getLogger("bake").debug("bake debug appears")
            logging.getLogger("test").debug("test debug suppressed")
            logging.getLogger("test").warning("test warning appears")

            captured = capsys.readouterr()

        assert "bake debug appears" in captured.err
        assert "test debug suppressed" not in captured.err
        assert "test warning appears" in captured.err


class TestBakeLogValidation:
    @pytest.mark.parametrize(
        "bake_log",
        [
            "info,myapp=debug,myapp.db=warning",
            "warning,bake=debug",
            "debug",
            "critical,myapp=trace",
        ],
    )
    def test_valid_bake_log(self, bake_log: str) -> None:
        bb = Bakebook(bake_log=bake_log)
        assert bb.bake_log == bake_log

    @pytest.mark.parametrize(
        "bake_log, match",
        [
            ("", "non-empty string"),
            ("warn", "Invalid BAKE_LOG level 'warn'"),
            ("=debug", "empty module name"),
            ("myapp=bad", "Invalid BAKE_LOG level 'bad'"),
            ("myapp=debug", "default logging level"),
        ],
    )
    def test_invalid_bake_log_raises(self, bake_log: str, match: str) -> None:
        with pytest.raises(Exception, match=match):
            Bakebook(bake_log=bake_log)


class TestBakeLogSubclassDefaults:
    def test_serialize_as_default_value(self) -> None:
        class MyBakebook(Bakebook):
            bake_log: str = serialize_bake_log({"": logging.DEBUG, "bake": logging.WARNING})

        bb = MyBakebook()
        assert bb.bake_log == "debug,bake=warning"

    def test_serialize_with_parse_override_default(self) -> None:
        class MyBakebook(Bakebook):
            bake_log: str = serialize_bake_log(
                {**parse_bake_log(DEFAULT_BAKE_LOG), "custom.logger": logging.DEBUG}
            )

        bb = MyBakebook()
        assert "custom.logger=debug" in bb.bake_log
        # Round-trip to verify structure
        level_per_module = parse_bake_log(bb.bake_log)
        assert "" in level_per_module
        assert level_per_module["custom.logger"] == logging.DEBUG

    def test_instance_override_takes_precedence(self) -> None:
        class MyBakebook(Bakebook):
            bake_log: str = serialize_bake_log({"": logging.DEBUG, "bake": logging.WARNING})

        bb = MyBakebook(bake_log="info")
        assert bb.bake_log == "info"


class TestExcludeCommandMethods:
    def test_exclude_uses_method_name_not_command_name(self) -> None:
        """__exclude_command_methods__ uses method name, not command name."""

        class ParentBakebook(Bakebook):
            @command(name="deploy-prod")
            def deploy_to_production(self):
                return "deploying"

            @command()
            def build(self):
                return "building"

        class ChildBakebook(ParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["deploy_to_production"]

        child = ChildBakebook()
        assert_commands(
            child,
            {
                "build": ExpectedCommand(
                    name="build", command_type=types.MethodType, output="building"
                ),
            },
            msg="ChildBakebook excludes by method name, not command name",
        )

    def test_grandchild_overrides_parent_exclude(self) -> None:
        """Grandchild's __exclude_command_methods__ overrides parent's."""

        class GrandParentBakebook(Bakebook):
            @command()
            def legacy(self):
                return "legacy"

            @command()
            def deploy(self):
                return "deploying"

        class ParentBakebook(GrandParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["legacy"]

        class ChildBakebook(ParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["deploy"]

        child = ChildBakebook()
        assert_commands(
            child,
            {
                "legacy": ExpectedCommand(
                    name="legacy", command_type=types.MethodType, output="legacy"
                ),
            },
            msg="Child's exclude overrides parent's (legacy restored, deploy excluded)",
        )

    def test_cannot_set_exclude_on_instance(self) -> None:
        """Pydantic enforces ClassVar cannot be set on instance (plain Python allows it)."""

        class ParentBakebook(Bakebook):
            @command()
            def deploy(self):
                return "deploying"

        class ChildBakebook(ParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["deploy"]

        child = ChildBakebook()
        with pytest.raises(AttributeError, match=r"is a ClassVar.*cannot be set on an instance"):
            __exclude_command_methods__: list[str] = ["build"]
            child.__exclude_command_methods__ = __exclude_command_methods__  # ty: ignore[invalid-attribute-access]

    def test_child_can_manually_extend_parent_exclusions(self) -> None:
        """Child can extend parent's __exclude_command_methods__ using manual list concatenation."""

        class ParentBakebook(Bakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["test", "debug"]

            @command()
            def test(self):
                return "testing"

            @command()
            def debug(self):
                return "debugging"

            @command()
            def deploy(self):
                return "deploying"

            @command()
            def build(self):
                return "building"

        class ChildBakebook(ParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = [
                *ParentBakebook.__exclude_command_methods__,
                "deploy",
            ]

        child = ChildBakebook()
        assert_commands(
            child,
            {
                "build": ExpectedCommand(
                    name="build", command_type=types.MethodType, output="building"
                ),
            },
            msg="Child manually extends parent's exclusions (test, debug, deploy)",
        )
