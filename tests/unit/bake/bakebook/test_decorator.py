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
