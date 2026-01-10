import types

from bake import Bakebook, command
from tests.bake.bakebook.utils import ExpectedCommand, assert_commands


class AbstractBakebook1(Bakebook):
    field1: str = "value1"

    @command()
    def action1(self) -> str:
        return f"action1: {self.field1}"


class ConcreteBakebook1A(AbstractBakebook1):
    field1: str = "concrete1a"

    @command()
    def action1(self) -> str:
        return f"concrete1a: {self.field1}"


class ConcreteBakebook1B(AbstractBakebook1):
    field1: str = "concrete1b"

    def action1(self) -> str:
        # Override method behavior, but no @command (inherits registration)
        return f"concrete1b override: {self.field1}"


class AbstractBakebook2(Bakebook):
    field2: str = "value2"

    @command()
    def action2(self) -> str:
        return f"action2: {self.field2}"


class ConcreteBakebook2A(AbstractBakebook2):
    field2: str = "concrete2a"

    @command()
    def action2(self) -> str:
        return f"concrete2a: {self.field2}"


class ConcreteBakebook2B(AbstractBakebook2):
    field2: str = "concrete2b"

    def action2(self) -> str:
        # Override method behavior, but no @command (inherits registration)
        return f"concrete2b override: {self.field2}"


class MyBakebook(AbstractBakebook1, AbstractBakebook2):
    pass


def test_multiple_recipes() -> None:
    bakebook = MyBakebook()

    assert bakebook.field1 == "value1"
    assert bakebook.field2 == "value2"


def test_multiple_recipes_with_custom_values() -> None:
    bakebook = MyBakebook(field1="custom1", field2="custom2")

    assert bakebook.field1 == "custom1"
    assert bakebook.field2 == "custom2"


def test_concrete_implementations() -> None:
    class BakebookWith1A(ConcreteBakebook1A, AbstractBakebook2):
        pass

    class BakebookWith1B(ConcreteBakebook1B, AbstractBakebook2):
        pass

    bakebook_a = BakebookWith1A()
    bakebook_b = BakebookWith1B()

    assert bakebook_a.field1 == "concrete1a"
    assert bakebook_b.field1 == "concrete1b"
    assert bakebook_a.field2 == "value2"
    assert bakebook_b.field2 == "value2"

    @bakebook_a.command()
    @bakebook_b.command()
    def some_action():
        return "some_action"

    assert_commands(
        bakebook=bakebook_a,
        expected_commands={
            "action1": ExpectedCommand(
                name="action1", command_type=types.MethodType, output="concrete1a: concrete1a"
            ),
            "action2": ExpectedCommand(
                name="action2", command_type=types.MethodType, output="action2: value2"
            ),
            "some_action": ExpectedCommand(
                name="some_action", command_type=types.FunctionType, output="some_action"
            ),
        },
        msg="BakebookWith1A",
    )

    assert_commands(
        bakebook=bakebook_b,
        expected_commands={
            "action2": ExpectedCommand(
                name="action2", command_type=types.MethodType, output="action2: value2"
            ),
            "some_action": ExpectedCommand(
                name="some_action", command_type=types.FunctionType, output="some_action"
            ),
        },
        msg="BakebookWith1B",
    )
