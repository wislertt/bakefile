import types

from bake import Bakebook, command
from tests.bake.bakebook.utils import ExpectedCommand, assert_commands


def test_multiple_recipes() -> None:
    class AbstractBakebook1(Bakebook):
        field1: str = "value1"

        @command()
        def action1(self) -> str:
            return f"action1: {self.field1}"

    class AbstractBakebook2(Bakebook):
        field2: str = "value2"

        @command()
        def action2(self) -> str:
            return f"action2: {self.field2}"

    class MyBakebook(AbstractBakebook1, AbstractBakebook2):
        pass

    bakebook = MyBakebook()
    assert bakebook.field1 == "value1"
    assert bakebook.field2 == "value2"


def test_multiple_recipes_with_custom_values() -> None:
    class AbstractBakebook1(Bakebook):
        field1: str = "value1"

    class AbstractBakebook2(Bakebook):
        field2: str = "value2"

    class MyBakebook(AbstractBakebook1, AbstractBakebook2):
        pass

    bakebook = MyBakebook(field1="custom1", field2="custom2")
    assert bakebook.field1 == "custom1"
    assert bakebook.field2 == "custom2"


def test_concrete_implementations() -> None:
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
            return f"concrete1b override: {self.field1}"

    class AbstractBakebook2(Bakebook):
        field2: str = "value2"

        @command()
        def action2(self) -> str:
            return f"action2: {self.field2}"

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
            "action1": ExpectedCommand(
                name="action1",
                command_type=types.MethodType,
                output="concrete1b override: concrete1b",
            ),
            "action2": ExpectedCommand(
                name="action2", command_type=types.MethodType, output="action2: value2"
            ),
            "some_action": ExpectedCommand(
                name="some_action", command_type=types.FunctionType, output="some_action"
            ),
        },
        msg="BakebookWith1B",
    )


def test_mro_order_effects() -> None:
    """Test that MRO order determines which parent's field/command wins."""

    class LeftBakebook(Bakebook):
        value: str = "left"

        @command()
        def run(self) -> str:
            return "run_left"

    class RightBakebook(Bakebook):
        value: str = "right"

        @command()
        def run(self) -> str:
            return "run_right"

    class LeftFirst(LeftBakebook, RightBakebook):
        pass

    left_first = LeftFirst()
    assert left_first.value == "left"
    assert left_first.run() == "run_left"

    class RightFirst(RightBakebook, LeftBakebook):
        pass

    right_first = RightFirst()
    assert right_first.value == "right"
    assert right_first.run() == "run_right"


def test_field_name_conflicts() -> None:
    class FirstBakebook(Bakebook):
        value: str = "first"

    class SecondBakebook(Bakebook):
        value: str = "second"

    class CombinedBakebook(FirstBakebook, SecondBakebook):
        pass

    bakebook = CombinedBakebook()
    assert bakebook.value == "first"


def test_command_name_conflicts() -> None:
    class FirstBakebook(Bakebook):
        @command()
        def run(self) -> str:
            return "first"

    class SecondBakebook(Bakebook):
        @command()
        def run(self) -> str:
            return "second"

    class CombinedBakebook(FirstBakebook, SecondBakebook):
        pass

    bakebook = CombinedBakebook()
    assert bakebook.run() == "first"

    assert_commands(
        bakebook,
        {
            "run": ExpectedCommand(name="run", command_type=types.MethodType, output="first"),
        },
        msg="Same command name - leftmost parent wins",
    )


def test_deep_inheritance_chain() -> None:
    class Level1(Bakebook):
        level1_field: str = "level1"

        @command()
        def action(self) -> str:
            return "level1"

    class Level2(Level1):
        level2_field: str = "level2"

        @command()
        def action(self) -> str:
            return "level2"

    class Level3(Level2):
        level3_field: str = "level3"

        @command()
        def action(self) -> str:
            return "level3"

    class FinalBakebook(Level3):
        pass

    bakebook = FinalBakebook()

    assert bakebook.level1_field == "level1"
    assert bakebook.level2_field == "level2"
    assert bakebook.level3_field == "level3"
    assert bakebook.action() == "level3"

    assert_commands(
        bakebook,
        {
            "action": ExpectedCommand(
                name="action", command_type=types.MethodType, output="level3"
            ),
        },
        msg="Deep inheritance chain",
    )

    class FinalBakebook2(Level3, Level2, Level1):
        pass

    bakebook2 = FinalBakebook2()
    assert bakebook2.level1_field == "level1"
    assert bakebook2.level2_field == "level2"
    assert bakebook2.level3_field == "level3"
    assert bakebook2.action() == "level3"

    assert_commands(
        bakebook2,
        {
            "action": ExpectedCommand(
                name="action", command_type=types.MethodType, output="level3"
            ),
        },
        msg="Deep inheritance with redundant parents - same result",
    )


def test_skip_intermediate_parent() -> None:
    """Test that skipping intermediate parent in inheritance still works."""

    class Level1(Bakebook):
        level1_field: str = "level1"

        @command()
        def action(self) -> str:
            return "level1"

    class Level2(Level1):
        level2_field: str = "level2"

        @command()
        def action(self) -> str:
            return "level2"

    class Level3(Level2):
        level3_field: str = "level3"

        @command()
        def action(self) -> str:
            return "level3"

    class SkipLevel2(Level3, Level1):
        pass

    bakebook = SkipLevel2()
    assert bakebook.level1_field == "level1"
    assert bakebook.level3_field == "level3"
    assert bakebook.level2_field == "level2"
    assert bakebook.action() == "level3"


def test_method_override_without_command_inherits_registration() -> None:
    """Test that method override without @command inherits parent's command registration."""

    class ParentBakebook(Bakebook):
        @command()
        def run(self) -> str:
            return "parent"

    class ChildBakebook(ParentBakebook):
        def run(self) -> str:
            return "child"

    class GrandChildBakebook(ChildBakebook):
        def run(self) -> str:
            return "grandchild"

    bakebook = GrandChildBakebook()
    assert bakebook.run() == "grandchild"
    # run command is inherited from ParentBakebook
    assert len(bakebook._app.registered_commands) == 1


def test_method_override_with_command_replaces_registration() -> None:
    """Test that method override WITH @command replaces parent's command registration."""

    class ParentBakebook(Bakebook):
        @command()
        def run(self) -> str:
            return "parent"

    class ChildBakebook(ParentBakebook):
        @command()
        def run(self) -> str:
            return "child"

    bakebook = ChildBakebook()
    assert bakebook.run() == "child"

    assert_commands(
        bakebook,
        {
            "run": ExpectedCommand(name="run", command_type=types.MethodType, output="child"),
        },
        msg="Method override WITH @command - replaces parent registration",
    )


def test_diamond_inheritance() -> None:
    r"""Test diamond inheritance pattern - A appears only once in MRO.

        A
       / \
      B   C
       \ /
        D
    """

    class BaseA(Bakebook):
        a_value: str = "from_A"

        @command()
        def run(self) -> str:
            return "A"

    class LeftB(BaseA):
        b_value: str = "from_B"

    class RightB(BaseA):
        c_value: str = "from_C"

    class DiamondBakebook(LeftB, RightB):
        pass

    bakebook = DiamondBakebook()

    assert bakebook.a_value == "from_A"
    assert bakebook.b_value == "from_B"
    assert bakebook.c_value == "from_C"
    assert bakebook.run() == "A"

    mro_names = [
        cls.__name__
        for cls in DiamondBakebook.__mro__
        if cls.__name__ not in ("object", "BaseModel")
    ]
    assert mro_names.count("BaseA") == 1

    assert_commands(
        bakebook,
        {
            "run": ExpectedCommand(name="run", command_type=types.MethodType, output="A"),
        },
        msg="Diamond inheritance - BaseA appears once",
    )
