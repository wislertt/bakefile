import types
from typing import ClassVar, Generic, TypeVar

import pytest
from pydantic import BaseModel, PrivateAttr
from pydantic_settings import SettingsConfigDict

from bake import Bakebook, BakebookMixin, command
from bake.bakebook.bakebook import _remerge_private_attributes_mro
from bake.utils.exceptions import FieldMroConflictError
from tests.unit.bake.bakebook.utils import ExpectedCommand, assert_commands

E = TypeVar("E")


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


def test_private_attr_override_survives_mixed_bases() -> None:
    class SpaceBase(Bakebook):
        _knob: str = "base-default"

    class OverrideSpace(SpaceBase):
        _knob: str = "override"

    class PlainSpace(SpaceBase):
        pass

    class HouseOrder(OverrideSpace, PlainSpace):
        pass

    class SwappedOrder(PlainSpace, OverrideSpace):
        pass

    assert HouseOrder()._knob == "override"
    assert SwappedOrder()._knob == "override"


def test_private_attr_first_base_wins_on_conflict() -> None:
    class FirstSpace(Bakebook):
        _knob: str = "first"

    class SecondSpace(Bakebook):
        _knob: str = "second"

    class Composed(FirstSpace, SecondSpace):
        pass

    assert Composed()._knob == "first"


def test_private_attr_declared_on_composed_class_wins() -> None:
    class SpaceA(Bakebook):
        _knob: str = "base-default"

    class SpaceB(Bakebook):
        pass

    class Composed(SpaceA, SpaceB):
        _knob: str = "own"

    assert Composed()._knob == "own"


def test_private_attr_factory_override_follows_mro() -> None:
    # Factories compare equal under value equality — only identity separates them.
    class SpaceBase(Bakebook):
        _knob: str = PrivateAttr(default_factory=lambda: "base-factory")

    class OverrideSpace(SpaceBase):
        _knob: str = PrivateAttr(default_factory=lambda: "override-factory")

    class PlainSpace(SpaceBase):
        pass

    class Composed(OverrideSpace, PlainSpace):
        _knob: str = PrivateAttr(default_factory=lambda: "own-factory")

    assert Composed()._knob == "own-factory"

    class NoOwnDeclaration(OverrideSpace, PlainSpace):
        pass

    assert NoOwnDeclaration()._knob == "override-factory"


def test_private_attr_with_bakebook_mixin_composition() -> None:
    """House composition shape: BakebookMixin fields first, spaces after."""

    class SpaceBase(Bakebook):
        _knob: str = "base-default"

    class OverrideSpace(SpaceBase):
        _knob: str = "override"

    class PlainSpace(SpaceBase):
        pass

    class ValueMixin(BakebookMixin):
        some_field: str = "x"

    class Real(ValueMixin, OverrideSpace, PlainSpace):
        pass

    bakebook = Real()
    assert bakebook._knob == "override"
    assert bakebook.some_field == "x"


def test_private_attr_instance_assignment_still_wins() -> None:
    """Per-instance values keep working — the knob stays a private attr."""

    class SpaceBase(Bakebook):
        _knob: str = "base-default"

    class OverrideSpace(SpaceBase):
        _knob: str = "override"

    class PlainSpace(SpaceBase):
        pass

    class Composed(OverrideSpace, PlainSpace):
        pass

    bakebook = Composed()
    bakebook._knob = "per-instance"
    assert bakebook._knob == "per-instance"
    assert Composed()._knob == "override"


def test_attr_kinds_follow_mro_in_bug_shape() -> None:
    # Shared-parent shape, override base declared first: every attr kind
    # resolves MRO-correct. Swapped order raises for the field; see
    # test_field_override_swapped_base_order_raises.
    class MatrixBase(Bakebook):
        plain_field: str = "base-field"
        class_var: ClassVar[str] = "base-classvar"

        @command()
        def cmd(self) -> str:
            return "base-cmd"

        def method(self) -> str:
            return "base-method"

    class MatrixOverride(MatrixBase):
        plain_field: str = "override-field"
        class_var: ClassVar[str] = "override-classvar"

        @command()
        def cmd(self) -> str:
            return "override-cmd"

        def method(self) -> str:
            return "override-method"

    class MatrixPlain(MatrixBase):
        pass

    class Composed(MatrixOverride, MatrixPlain):
        pass

    bakebook = Composed()
    assert bakebook.plain_field == "override-field"
    assert bakebook.class_var == "override-classvar"
    assert bakebook.method() == "override-method"

    assert_commands(
        bakebook,
        {
            "cmd": ExpectedCommand(
                name="cmd", command_type=types.MethodType, output="override-cmd"
            ),
        },
        msg="Composed: marked method registration follows MRO",
    )


def test_non_field_kinds_follow_mro_in_swapped_shape() -> None:
    # No pydantic fields: ClassVars/methods/@command resolve natively, so both
    # base orders agree.
    class MatrixBase(Bakebook):
        class_var: ClassVar[str] = "base-classvar"

        @command()
        def cmd(self) -> str:
            return "base-cmd"

        def method(self) -> str:
            return "base-method"

    class MatrixOverride(MatrixBase):
        class_var: ClassVar[str] = "override-classvar"

        @command()
        def cmd(self) -> str:
            return "override-cmd"

        def method(self) -> str:
            return "override-method"

    class MatrixPlain(MatrixBase):
        pass

    for cls in (
        type("Composed", (MatrixOverride, MatrixPlain), {}),
        type("Swapped", (MatrixPlain, MatrixOverride), {}),
    ):
        bakebook = cls()
        assert bakebook.class_var == "override-classvar", cls.__name__
        assert bakebook.method() == "override-method", cls.__name__
        assert bakebook.cmd() == "override-cmd", cls.__name__

        assert_commands(
            bakebook,
            {
                "cmd": ExpectedCommand(
                    name="cmd", command_type=types.MethodType, output="override-cmd"
                ),
            },
            msg=f"{cls.__name__}: marked method registration follows MRO",
        )


def test_field_override_swapped_base_order_raises() -> None:
    class MatrixBase(Bakebook):
        plain_field: str = "base-field"

    class MatrixOverride(MatrixBase):
        plain_field: str = "override-field"

    class MatrixPlain(MatrixBase):
        pass

    with pytest.raises(FieldMroConflictError, match="plain_field") as exc_info:

        class Swapped(MatrixPlain, MatrixOverride):
            pass

    message = str(exc_info.value)
    assert "MatrixPlain" in message
    assert "MatrixOverride" in message
    assert "redeclare" in message
    assert "BakebookMixin" in message


def test_field_merge_own_redeclaration_wins() -> None:
    class MatrixBase(Bakebook):
        plain_field: str = "base-field"

    class MatrixOverride(MatrixBase):
        plain_field: str = "override-field"

    class MatrixPlain(MatrixBase):
        pass

    class Redeclared(MatrixPlain, MatrixOverride):
        plain_field: str = "override-field"

    assert Redeclared().plain_field == "override-field"


def test_field_merge_diamond_single_declarer_no_raise() -> None:
    class SpaceBase(Bakebook):
        knob: str = "base"

    class LeftSpace(SpaceBase):
        pass

    class RightSpace(SpaceBase):
        pass

    class Diamond(LeftSpace, RightSpace):
        pass

    assert Diamond().knob == "base"


def test_field_merge_identical_redeclare_across_branches_no_raise() -> None:
    class SpaceBase(Bakebook):
        knob: str = "base"

    class SameLeft(SpaceBase):
        knob: str = "same"

    class SameRight(SpaceBase):
        knob: str = "same"

    class Composed(SameLeft, SameRight):
        pass

    assert Composed().knob == "same"


def test_field_merge_both_declared_swapped_follows_declared_order() -> None:
    class SpaceBase(Bakebook):
        knob: str = "base"

    class OverrideSpace(SpaceBase):
        knob: str = "override"

    class Override2Space(SpaceBase):
        knob: str = "override2"

    class Swapped(Override2Space, OverrideSpace):
        pass

    assert Swapped().knob == "override2"


def test_field_merge_mixin_first_wins() -> None:
    class SpaceBase(Bakebook):
        knob: str = "base"

    class OverrideSpace(SpaceBase):
        knob: str = "override"

    class PlainSpace(SpaceBase):
        pass

    class KnobMixin(BakebookMixin):
        knob: str = "mixin"

    class Composed(KnobMixin, OverrideSpace, PlainSpace):
        pass

    assert Composed().knob == "mixin"


def test_field_merge_raises_mixin_after_overriding_space() -> None:
    # The documented footgun: a mixin listed after the spaces silently lost;
    # now rejected loudly.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class OverrideSpace(SpaceBase):
        knob: str = "override"

    class PlainSpace(SpaceBase):
        pass

    class KnobMixin(BakebookMixin):
        knob: str = "mixin"

    with pytest.raises(FieldMroConflictError, match="knob"):

        class Composed(PlainSpace, OverrideSpace, KnobMixin):
            pass


def test_field_merge_mixin_after_space_matches_mro() -> None:
    # Two-base mixin-late is NOT the bug: SpaceBase precedes the mixin in the
    # MRO natively too.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class PlainSpace(SpaceBase):
        pass

    class KnobMixin(BakebookMixin):
        knob: str = "mixin"

    class Composed(PlainSpace, KnobMixin):
        pass

    assert Composed().knob == "base"


def test_field_merge_parametrized_alias_creation_no_raise() -> None:
    class GenericKnobSpace(Bakebook, Generic[E]):
        knob: E

    aliased = GenericKnobSpace[str]

    assert aliased.__pydantic_fields__["knob"].annotation is str


def test_field_merge_parametrized_generic_base_no_raise() -> None:
    # Parametrized generic bases fill fields via generic machinery, not
    # class-body annotations; pydantic resolves the substituted copy correctly.
    class GenericKnobSpace(Bakebook, Generic[E]):
        knob: E

    class OtherSpace(Bakebook):
        other: str = "other"

    class Composed(OtherSpace, GenericKnobSpace[str]):
        pass

    assert Composed.__pydantic_fields__["knob"].annotation is str
    assert Composed(knob="from-kwargs").knob == "from-kwargs"


def test_field_merge_parametrized_generic_three_bases_no_raise() -> None:
    # data-kit GLZServiceSpace shape: 'knob' lives only on the generic branch.
    class GenericKnobSpace(Bakebook, Generic[E]):
        knob: E

    class ToolsSpace(Bakebook):
        tool: str = "tool"

    class ServiceSpace(Bakebook):
        service: str = "service"

    class Composed(ToolsSpace, GenericKnobSpace[str], ServiceSpace):
        pass

    assert Composed.__pydantic_fields__["knob"].annotation is str
    assert Composed(knob="from-kwargs").knob == "from-kwargs"


def test_field_merge_generic_alias_first_wins_no_raise() -> None:
    class SpaceBase(Bakebook):
        knob: str = "base"

    class GenericOverrideSpace(SpaceBase, Generic[E]):
        knob: E

    class PlainSpace(SpaceBase):
        pass

    class Composed(GenericOverrideSpace[str], PlainSpace):
        pass

    # The generic branch's required knob wins — not SpaceBase's defaulted one.
    assert Composed.__pydantic_fields__["knob"].is_required()
    assert Composed(knob="override").knob == "override"


def test_field_merge_generic_branch_bug_shape_still_raises() -> None:
    # Detection still fires: the plain sibling's inherited snapshot beats the
    # alias's substituted override.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class GenericOverrideSpace(SpaceBase, Generic[E]):
        knob: E

    class PlainSpace(SpaceBase):
        pass

    with pytest.raises(FieldMroConflictError, match="knob"):

        class Swapped(PlainSpace, GenericOverrideSpace[str]):
            pass


def test_field_merge_generic_alias_does_not_claim_inherited_field() -> None:
    # The alias claims only names its chain re-declares; inherited 'knob'
    # stays with declarer SpaceBase and raises nothing.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class GenericSiblingSpace(SpaceBase, Generic[E]):
        other: E

    class PlainSpace(SpaceBase):
        pass

    class Composed(PlainSpace, GenericSiblingSpace[str]):
        pass

    assert Composed(other="sibling").knob == "base"
    assert Composed(other="sibling").other == "sibling"


def test_field_merge_classvar_declarer_before_field_no_raise() -> None:
    # get_annotations lists ClassVar names too: the MRO-first declarer is the
    # ClassVar base, which shadows natively and has no field entry.
    class VarFirst(Bakebook):
        knob: ClassVar[str] = "var"

    class FieldLater(Bakebook):
        knob: str = "field"

    class Composed(VarFirst, FieldLater):
        pass

    assert Composed.knob == "var"
    # pydantic drops the field entirely under a MRO-first ClassVar declarer.
    assert "knob" not in Composed.__pydantic_fields__


def test_field_merge_generic_subclass_alias_no_raise() -> None:
    # Substitution flows through the whole chain even without redeclaration,
    # so the alias's copy is the correct resolution.
    class GenericKnobSpace(Bakebook, Generic[E]):
        knob: E

    class SubSpace(GenericKnobSpace[E]):
        extra: str = "extra"

    class OtherSpace(Bakebook):
        other: str = "other"

    class Composed(OtherSpace, SubSpace[str]):
        pass

    assert Composed.__pydantic_fields__["knob"].annotation is str
    bakebook = Composed(knob="from-kwargs")
    assert bakebook.knob == "from-kwargs"
    assert bakebook.extra == "extra"


def test_field_merge_generic_subclass_alias_bug_shape_still_raises() -> None:
    # Detection survives subclass aliases: inherited snapshot still shadows
    # the substituted override.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class GenericOverrideSpace(SpaceBase, Generic[E]):
        knob: E

    class SubOverrideSpace(GenericOverrideSpace[E]):
        extra: str = "extra"

    class PlainSpace(SpaceBase):
        pass

    with pytest.raises(FieldMroConflictError, match="knob"):

        class Swapped(PlainSpace, SubOverrideSpace[str]):
            pass


def test_field_merge_alias_does_not_claim_parallel_branch_field() -> None:
    # 'knob' comes from a parallel branch, so the alias does not claim it —
    # its inherited snapshot shadows the override and still raises.
    class SpaceBase(Bakebook):
        knob: str = "base"

    class GenericSiblingSpace(SpaceBase, Generic[E]):
        other: E

    class OverrideSpace(SpaceBase):
        knob: str = "override"

    with pytest.raises(FieldMroConflictError, match="knob"):

        class Swapped(GenericSiblingSpace[str], OverrideSpace):
            pass


def test_field_merge_two_aliases_first_claim_wins() -> None:
    class GenericKnobSpace(Bakebook, Generic[E]):
        knob: E

    class BranchASpace(GenericKnobSpace[E]):
        pass

    class BranchBSpace(GenericKnobSpace[E]):
        pass

    class Composed(BranchASpace[str], BranchBSpace[str]):
        pass

    # The first alias's claim stands; the second does not re-claim.
    assert Composed.__pydantic_fields__["knob"].annotation is str


def test_field_merge_alias_with_classvar_declarer_no_raise() -> None:
    # ClassVar declarers have no field entry: the claim loop skips them, and
    # the expected_field-is-None path applies.
    class VarFirst(Bakebook):
        knob: ClassVar[str] = "var"

    class FieldLater(Bakebook):
        knob: str = "field"

    class GenericMiddle(FieldLater, Generic[E]):
        other: E

    class Composed(VarFirst, GenericMiddle[str]):
        pass

    assert Composed.knob == "var"
    assert Composed(knob="from-kwargs", other="from-kwargs").other == "from-kwargs"


def test_remerge_skips_class_without_private_attributes() -> None:
    class NoSnapshotModel(BaseModel):
        _knob: str = "own"

    del NoSnapshotModel.__private_attributes__

    _remerge_private_attributes_mro(NoSnapshotModel)

    assert "__private_attributes__" not in NoSnapshotModel.__dict__


def test_remerge_skips_single_pydantic_base() -> None:
    class DirectModel(BaseModel):
        _knob: str = "own"

    snapshot = DirectModel.__dict__["__private_attributes__"]

    _remerge_private_attributes_mro(DirectModel)

    assert DirectModel.__dict__["__private_attributes__"] is snapshot


@pytest.mark.xfail(
    strict=True,
    reason="pydantic/pydantic#11700 — once this XPasses, upstream fixed the "
    "declared-order private-attr merge: remove this test and revisit "
    "_remerge_private_attributes_mro in bake/bakebook/bakebook.py",
)
def test_pydantic_raw_private_attr_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the Bakebook-level tests above pass either
    way and cannot signal an upstream fix."""

    class RawBase(BaseModel):
        _knob: str = "base"

    class RawOverride(RawBase):
        _knob: str = "override"

    class RawPlain(RawBase):
        pass

    class RawComposed(RawOverride, RawPlain):
        pass

    assert RawComposed()._knob == "override"


@pytest.mark.xfail(
    strict=True,
    reason="pydantic resolves fields from flattened base snapshots in "
    "declared-base order, so an inherited copy shadows a later base's "
    "override (pydantic/pydantic#13678; kin of #11700, no v2 fix planned). "
    "Once this XPasses, upstream fixed it: remove FieldMroConflictError "
    "and _check_field_merge_mro from bake/bakebook/bakebook.py",
)
def test_pydantic_raw_field_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the Bakebook-level raise cannot signal an
    upstream fix because Bakebook rejects the shape at class creation."""

    class RawBase(BaseModel):
        f: str = "base"

    class RawOverride(RawBase):
        f: str = "override"

    class RawPlain(RawBase):
        pass

    class RawSwapped(RawPlain, RawOverride):
        pass

    assert RawSwapped().f == "override"


@pytest.mark.xfail(
    strict=True,
    reason="pydantic merges base model_configs in declared-base order, "
    "last wins, so Bakebook's shadows an earlier mixin's "
    "(pydantic/pydantic#9992, documented, v3 fix planned). Once this "
    "XPasses, upstream fixed it: drop the model_config note from "
    "BakebookMixin's docstring in bake/bakebook/bakebook.py",
)
def test_pydantic_raw_model_config_mro_bug_still_present() -> None:
    """Pins the raw pydantic bug; the docstring note has no other tripwire."""

    class RawEnvMixin(BakebookMixin):
        model_config = SettingsConfigDict(env_file=".myenv")

    class RawBook(RawEnvMixin, Bakebook):
        pass

    assert RawBook.model_config["env_file"] == ".myenv"
