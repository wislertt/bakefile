import inspect
from typing import ClassVar

import pytest
import typer
from typer.testing import CliRunner

from bake import Bakebook, command, console
from bake.utils.exceptions import CommandConflictError
from tests.unit.bake.bakebook.utils import assert_signature_matches_typer

runner = CliRunner()


def test_command_signature_matches_typer() -> None:
    assert_signature_matches_typer(
        inspect.signature(command),
        "command",
        skip_self=True,
        extra_params=["group_name"],  # Bakebook-specific parameter
    )


class TestCommandGroups:
    """Tests for command group functionality."""

    def test_command_with_group_name_creates_group(self) -> None:
        """A command with group_name should create a command group."""

        class MyBakebook(Bakebook):
            @command(name="list", group_name="items")
            def _items_list(self) -> str:
                return "items list"

        bakebook = MyBakebook()

        # Group should be created
        assert "items" in bakebook._command_groups

    def test_multiple_commands_in_same_group(self) -> None:
        """Multiple commands with same group_name should be in the same group."""

        class MyBakebook(Bakebook):
            @command(name="list", group_name="items")
            def _items_list(self) -> str:
                return "items list"

            @command(name="get", group_name="items")
            def _items_get(self, name: str) -> str:
                return f"items get {name}"

        bakebook = MyBakebook()

        # Only one group should be created
        assert "items" in bakebook._command_groups
        assert len(bakebook._command_groups) == 1

    def test_multiple_groups(self) -> None:
        """Multiple groups should coexist."""

        class MyBakebook(Bakebook):
            @command(name="list", group_name="items")
            def _items_list(self) -> str:
                return "items list"

            @command(name="list", group_name="users")
            def _users_list(self) -> str:
                return "users list"

        bakebook = MyBakebook()

        assert "items" in bakebook._command_groups
        assert "users" in bakebook._command_groups
        assert len(bakebook._command_groups) == 2


class TestCommandConflicts:
    """Tests for conflict detection between commands and groups."""

    def test_command_conflicts_with_existing_group_raises_error(self) -> None:
        """Registering a command with same name as existing group should raise error."""

        class MyBakebook(Bakebook):
            @command(name="items", group_name="items")
            def _a_create_group(self) -> str:
                return "items list"

            @command(name="items")
            def _z_register_command(self) -> str:
                return "items command"

        # _a_create_group is registered first (alphabetically), creating group "items"
        # _z_register_command then fails because group "items" already exists
        with pytest.raises(
            CommandConflictError,
            match=r"Cannot register command 'items'.*group.*already exists",
        ):
            MyBakebook()

    def test_group_conflicts_with_existing_command_raises_error(self) -> None:
        """Creating a group with same name as existing command should raise error."""

        class MyBakebook(Bakebook):
            @command(name="items")
            def _items(self) -> str:
                return "items command"

            @command(name="list", group_name="items")
            def _items_list(self) -> str:
                return "items list"

        # _items is registered first (alphabetically), creating command "items"
        # _items_list then fails because command "items" already exists
        with pytest.raises(
            CommandConflictError,
            match=r"Cannot create command group 'items'.*command.*already exists",
        ):
            MyBakebook()

    def test_child_override_parent_command_with_exclude(self) -> None:
        """Child can override parent command using __exclude_command_methods__."""

        class ParentBakebook(Bakebook):
            @command()
            def list(self) -> str:
                return "items list"

        class ChildBakebook(ParentBakebook):
            __exclude_command_methods__: ClassVar[list[str]] = ["list"]  # Exclude parent's list

            @command(name="list")  # Define our own list
            def list2(self) -> str:
                return "items list from child"

        # Should work without error
        c = ChildBakebook()
        assert "list" in c._registered_commands

    def test_duplicate_command_names_raises_error(self) -> None:
        """Registering two commands with same name should raise error."""

        class MyBakebook(Bakebook):
            @command(name="foo")
            def _foo1(self) -> str:
                return "foo1"

            @command(name="foo")
            def _foo2(self) -> str:
                return "foo2"

        with pytest.raises(
            CommandConflictError,
            match=r"Cannot register command 'foo'.*already exists",
        ):
            MyBakebook()

    def test_explicit_group_conflicts_with_existing_command_raises_error(self) -> None:
        """Explicitly creating group with same name as existing command should error."""

        class MyBakebook(Bakebook):
            @command(name="items")
            def _items(self) -> str:
                return "items command"

            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._get_or_create_group("items")

        with pytest.raises(
            CommandConflictError,
            match=r"Cannot create command group 'items'.*command.*already exists",
        ):
            MyBakebook()

    def test_duplicate_command_names_in_same_group(self) -> None:
        """Registering two commands with same name in same group should raise error."""

        class MyBakebook(Bakebook):
            @command(name="list", group_name="items")
            def _items_list(self) -> str:
                return "items list"

            @command(name="list", group_name="items")
            def _items_list_2(self) -> str:
                return "items list 2"

        with pytest.raises(
            CommandConflictError,
            match=r"Cannot register command 'list' in group 'items'.*already exists",
        ):
            MyBakebook()


class TestExternalCommandRegistration:
    def test_last_registration_wins(self) -> None:

        class MyBakebook(Bakebook):
            @command()
            def foo(self):
                console.echo("from foo in MyBakebook")

        bakebook = MyBakebook()

        @bakebook.command()
        def foo():
            console.echo("from foo")

        @bakebook.command(name="foo")
        def foo2():
            console.echo("from foo2")

        result = runner.invoke(bakebook._app, ["foo"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "from foo2"

    def test_external_typer_app_as_command_group(self) -> None:
        class MyBakebook(Bakebook):
            @command()
            def foo(self):
                console.echo("from foo in MyBakebook")

        bakebook = MyBakebook()

        app = typer.Typer()

        @app.command()
        def bar():
            console.echo("from bar")

        bakebook._app.add_typer(app, name="foo")

        result = runner.invoke(bakebook._app, ["foo", "bar"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "from bar"

    def test_external_group_overwrites_command_with_same_name(self) -> None:
        """External Typer group overwrites command registered after it."""

        class MyBakebook(Bakebook):
            @command()
            def foo(self):
                console.echo("from foo in MyBakebook")

        bakebook = MyBakebook()

        app = typer.Typer()

        @app.command()
        def bar():
            console.echo("from bar")

        bakebook._app.add_typer(app, name="foo")

        @bakebook.command(name="foo")
        def foo():
            console.echo("from foo")

        result = runner.invoke(bakebook._app, ["foo", "bar"])
        assert result.exit_code == 0
        assert result.stdout.strip() == "from bar"  # group always win


class TestCommandWithStandardDecorators:
    """Tests for @command combined with @staticmethod and @classmethod."""

    def test_command_with_staticmethod_command_first(self) -> None:
        """@command followed by @staticmethod should work correctly."""

        class MyBakebook(Bakebook):
            @command(name="util")
            @staticmethod
            def my_util() -> None:
                console.echo("static utility")

        bakebook = MyBakebook()
        # Single command mode - invoke without command name
        result = runner.invoke(bakebook._app, [])
        assert result.exit_code == 0
        assert result.stdout.strip() == "static utility"

    def test_command_with_staticmethod_staticmethod_first(self) -> None:
        """@staticmethod followed by @command should work correctly."""

        class MyBakebook(Bakebook):
            @staticmethod
            @command(name="util")
            def my_util() -> None:
                console.echo("static utility")

        bakebook = MyBakebook()
        # Single command mode - invoke without command name
        result = runner.invoke(bakebook._app, [])
        assert result.exit_code == 0
        assert result.stdout.strip() == "static utility"

    def test_command_with_classmethod_command_first(self) -> None:
        """@command followed by @classmethod should work correctly."""

        class MyBakebook(Bakebook):
            @command(name="factory")
            @classmethod
            def create(cls) -> None:
                console.echo(f"created from {cls.__name__}")

        bakebook = MyBakebook()
        # Single command mode - invoke without command name
        result = runner.invoke(bakebook._app, [])
        assert result.exit_code == 0
        assert "created from MyBakebook" in result.stdout.strip()

    def test_command_with_classmethod_classmethod_first(self) -> None:
        """@classmethod followed by @command should work correctly."""

        class MyBakebook(Bakebook):
            @classmethod
            @command(name="factory")
            def create(cls) -> None:
                console.echo(f"created from {cls.__name__}")

        bakebook = MyBakebook()
        # Single command mode - invoke without command name
        result = runner.invoke(bakebook._app, [])
        assert result.exit_code == 0
        assert "created from MyBakebook" in result.stdout.strip()

    def test_staticmethod_command_is_registered(self) -> None:
        """A @staticmethod with @command should be registered in commands."""

        class MyBakebook(Bakebook):
            @command(name="util")
            @staticmethod
            def my_util() -> None:
                console.echo("static utility")

        bakebook = MyBakebook()
        assert "util" in bakebook._registered_commands

    def test_classmethod_command_is_registered(self) -> None:
        """A @classmethod with @command should be registered in commands."""

        class MyBakebook(Bakebook):
            @command(name="factory")
            @classmethod
            def create(cls) -> None:
                console.echo(f"created from {cls.__name__}")

        bakebook = MyBakebook()
        assert "factory" in bakebook._registered_commands

    def test_child_inherits_staticmethod_command(self) -> None:
        """Child class should inherit parent's @staticmethod @command."""

        class ParentBakebook(Bakebook):
            @staticmethod
            @command(name="util")
            def parent_util() -> None:
                console.echo("parent utility")

        class ChildBakebook(ParentBakebook):
            pass

        child = ChildBakebook()
        # Should inherit the parent's command
        assert "util" in child._registered_commands

        # Should be callable
        result = runner.invoke(child._app, [])
        assert result.exit_code == 0
        assert "parent utility" in result.stdout.strip()

    def test_child_inherits_classmethod_command(self) -> None:
        """Child class should inherit parent's @classmethod @command."""

        class ParentBakebook(Bakebook):
            @classmethod
            @command(name="factory")
            def create(cls) -> None:
                console.echo(f"created from {cls.__name__}")

        class ChildBakebook(ParentBakebook):
            pass

        child = ChildBakebook()
        # Should inherit the parent's command
        assert "factory" in child._registered_commands

        # Should be callable - should use ChildBakebook as cls
        result = runner.invoke(child._app, [])
        assert result.exit_code == 0
        assert "created from ChildBakebook" in result.stdout.strip()

    def test_child_shadows_parent_staticmethod_with_metadata_in_mro(self) -> None:
        """Child shadows parent's staticmethod; MRO search finds parent's @command metadata."""

        class ParentBakebook(Bakebook):
            @staticmethod
            @command(name="util")
            def shared_util() -> None:
                console.echo("parent utility")

        # Child shadows with non-decorated staticmethod - no metadata on child's version
        class ChildBakebook(ParentBakebook):
            @staticmethod
            def shared_util() -> None:
                console.echo("child utility")

        child = ChildBakebook()
        # Should find the parent's @command metadata through MRO
        assert "util" in child._registered_commands

        # Should call child's version (which shadows parent) but with parent's @command config
        result = runner.invoke(child._app, [])
        assert result.exit_code == 0
        assert "child utility" in result.stdout.strip()


class TestCommandWithLruCache:
    """Tests for @command combined with @functools.cache."""

    def test_lru_cache_command_is_registered(self) -> None:
        """A @functools.cache with @command should be registered in commands."""

        import functools

        class MyBakebook(Bakebook):
            @command()
            @functools.cache
            @staticmethod
            def cached(x: int) -> str:
                return f"cached: {x}"

        bakebook = MyBakebook()
        assert "cached" in bakebook._registered_commands


class TestCommandWithCustomDecorator:
    """Tests for @command combined with custom wrapper decorators."""

    def test_custom_decorator_command_is_registered(self) -> None:
        """A custom decorator with @command should be registered in commands."""

        import functools

        def custom_decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        class MyBakebook(Bakebook):
            @command()
            @custom_decorator
            def custom_op(self) -> str:
                return "custom result"

        bakebook = MyBakebook()
        assert "custom-op" in bakebook._registered_commands


class TestCommandWithAsync:
    """Tests for @command with async def."""

    def test_async_command_is_registered(self) -> None:
        """An async command should be registered in commands."""

        class MyBakebook(Bakebook):
            @command()
            async def async_op(self) -> None:
                console.echo("async result")

        bakebook = MyBakebook()
        assert "async-op" in bakebook._registered_commands
